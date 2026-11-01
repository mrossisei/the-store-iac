"""Contrasta topología de datos con AWS; devuelve únicamente evidencia sin passwords."""
from collections import Counter
import time

from acceso_kind import require
from ssm import aws


def redis_version_matches(actual, requested):
    # El API acepta major.minor (7.1) y el nodo informa su patch (7.1.0).
    return actual == requested or actual.startswith(requested + '.')


def ready_rds(region, identifier, seconds=900):
    # RDS puede devolver available antes de terminar la conversión Multi-AZ.
    # Esperar el dato real de standby, sin inferirlo de las subredes declaradas.
    deadline = time.monotonic() + seconds
    while True:
        db = aws(region, 'rds', 'describe-db-instances', '--db-instance-identifier', identifier)['DBInstances'][0]
        pending = db['DBInstanceStatus'] in ('creating', 'modifying', 'rebooting') or (
            db['DBInstanceStatus'] == 'available' and db['MultiAZ'] and not db.get('SecondaryAvailabilityZone'))
        if not pending or time.monotonic() >= deadline:
            return db
        time.sleep(15)


def check_rds(db, *, engine, version, vpc, subnets, security_group, zones, instance_class):
    require(db['DBInstanceStatus'] == 'available' and db['Engine'] == engine and db['EngineVersion'] == version, 'RDS no disponible o motor/version distinto')
    require(db['MultiAZ'] and db.get('SecondaryAvailabilityZone') and db['AvailabilityZone'] != db['SecondaryAvailabilityZone'] and {db['AvailabilityZone'], db['SecondaryAvailabilityZone']} == set(zones), 'RDS primaria/standby deben estar en las dos AZ distintas')
    require(not db['PubliclyAccessible'] and db['DBInstanceClass'] == instance_class and db['StorageType'] == 'gp2' and db['AllocatedStorage'] <= 100 and db['StorageEncrypted'] and db.get('MonitoringInterval', 0) == 0, 'RDS no cumple clase/privacidad/gp2/cifrado/monitoring del Lab')
    require(db['DBSubnetGroup']['VpcId'] == vpc and {s['SubnetIdentifier'] for s in db['DBSubnetGroup']['Subnets']} == set(subnets), 'RDS usa subredes ajenas a datos')
    require({g['VpcSecurityGroupId'] for g in db['VpcSecurityGroups']} == {security_group} and all(g['Status'] == 'active' for g in db['VpcSecurityGroups']), 'SG RDS incorrecto')
    return {'primary_az': db['AvailabilityZone'], 'standby_az': db['SecondaryAvailabilityZone'], 'engine': engine, 'version': version}


def check_data_sg(group, source):
    rules = group['IpPermissions']
    require(len(rules) == 3 and {r.get('FromPort') for r in rules} == {3306, 5432, 6379}, 'SG datos contiene puertos inesperados')
    for rule in rules:
        require(rule['IpProtocol'] == 'tcp' and rule['FromPort'] == rule['ToPort'] and not rule.get('IpRanges') and not rule.get('Ipv6Ranges') and not rule.get('PrefixListIds') and len(rule.get('UserIdGroupPairs', [])) == 1 and rule['UserIdGroupPairs'][0]['GroupId'] == source, 'Datos deben aceptar solo SG EC2, nunca un CIDR público/VPC')


def verify(values, environment, tools):
    region = environment['region']
    network, resources = values['network'], values['data_resources']
    zones = [environment['zones'][key]['availability_zone'] for key in ('a', 'b')]
    subnets = [s['id'] for s in network['db_subnets'].values()]
    result = {'rds': {}, 'redis': {}}
    group = aws(region, 'ec2', 'describe-security-groups', '--group-ids', resources['security_group_id'])['SecurityGroups'][0]
    require(group['VpcId'] == network['vpc_id'], 'SG de datos en otra VPC')
    check_data_sg(group, network['application_security_group_id'])
    for name, engine, version in [('mysql', 'mysql', tools['mysql_engine_version']), ('postgres', 'postgres', tools['postgres_engine_version'])]:
        db = ready_rds(region, resources[name + '_id'])
        result['rds'][name] = check_rds(db, engine=engine, version=version, vpc=network['vpc_id'], subnets=subnets, security_group=resources['security_group_id'], zones=zones, instance_class=tools['rds_class_candidate'])
    cache = aws(region, 'elasticache', 'describe-replication-groups', '--replication-group-id', resources['redis_id'])['ReplicationGroups'][0]
    require(cache['Status'] == 'available' and cache['AutomaticFailover'] == cache['MultiAZ'] == 'enabled' and cache['AtRestEncryptionEnabled'] and len(cache['NodeGroups']) == 1, 'Redis no tiene Multi-AZ/failover disponible')
    members = cache['NodeGroups'][0]['NodeGroupMembers']
    require(len(members) == 2 and Counter(m['CurrentRole'] for m in members) == Counter({'primary': 1, 'replica': 1}) and {m['PreferredAvailabilityZone'] for m in members} == set(zones), 'Redis requiere primaria/réplica en AZ diferentes')
    for member in members:
        node = aws(region, 'elasticache', 'describe-cache-clusters', '--cache-cluster-id', member['CacheClusterId'], '--show-cache-node-info')['CacheClusters'][0]
        require(node['CacheClusterStatus'] == 'available' and redis_version_matches(node['EngineVersion'], tools['redis_engine_version']) and node['CacheNodeType'] == tools['cache_node_type'] and node['CacheSubnetGroupName'] == resources['redis_subnet_group'] and {g['SecurityGroupId'] for g in node['SecurityGroups']} == {resources['security_group_id']}, 'Nodo Redis fuera de configuración esperada')
    result['redis'] = {m['CurrentRole']: m['PreferredAvailabilityZone'] for m in members}
    table = aws(region, 'dynamodb', 'describe-table', '--table-name', resources['dynamodb_table'])['Table']
    require(table['TableStatus'] == 'ACTIVE' and table['KeySchema'] == [{'AttributeName': 'id', 'KeyType': 'HASH'}], 'Tabla de carrito no activa o clave incompatible')
    indexes = [i for i in table['GlobalSecondaryIndexes'] if i['IndexName'] == 'idx_global_customerId']
    require(len(indexes) == 1 and indexes[0]['IndexStatus'] == 'ACTIVE' and indexes[0]['KeySchema'] == [{'AttributeName': 'customerId', 'KeyType': 'HASH'}], 'Índice customerId no activo/correcto')
    aws(region, 'sqs', 'get-queue-attributes', '--queue-url', resources['sqs_queue_url'], '--attribute-names', 'QueueArn')
    result['checks'] = ['rds-primary-standby-azs', 'redis-primary-replica-azs', 'data-sg-only-ec2', 'dynamodb-schema-gsi', 'sqs-exists']
    return result
