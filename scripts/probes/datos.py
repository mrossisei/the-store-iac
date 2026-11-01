#!/usr/bin/env python3
"""Sonda T06 ejecutada en EC2. Lee configuración privada; nunca imprime DSN/passwords."""
import json
import re
import sys
import time
from pathlib import Path

import boto3
from botocore.config import Config
import psycopg
import pymysql
import redis


class ProbeError(RuntimeError):
    pass


def require(value, message):
    if not value:
        raise ProbeError(message)


def eventually(read, expected, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if read() == expected:
            return
        time.sleep(0.5)
    raise ProbeError('La lectura no convergió al dato de esta ejecución')


def receive_owned(sqs, url, run_id, expected=None):
    """Retira solo mensajes propios; restaura visibilidad de cualquier otro."""
    deadline = time.monotonic() + (45 if expected else 15)
    found = False
    while time.monotonic() < deadline:
        response = sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=2, VisibilityTimeout=10)
        for message in response.get('Messages', []):
            try:
                body = json.loads(message['Body'])
            except (ValueError, TypeError):
                body = {}
            if isinstance(body, dict) and body.get('t06_run') == run_id:
                if expected is not None and body.get('writer') != expected:
                    sqs.change_message_visibility(QueueUrl=url, ReceiptHandle=message['ReceiptHandle'], VisibilityTimeout=0)
                    raise ProbeError('Evento de fase inesperada')
                try:
                    sqs.delete_message(QueueUrl=url, ReceiptHandle=message['ReceiptHandle'])
                except Exception:
                    try:
                        sqs.change_message_visibility(QueueUrl=url, ReceiptHandle=message['ReceiptHandle'], VisibilityTimeout=0)
                    except Exception:
                        pass
                    raise
                found = True
            else:
                sqs.change_message_visibility(QueueUrl=url, ReceiptHandle=message['ReceiptHandle'], VisibilityTimeout=0)
        if found and expected:
            return True
    require(not expected, 'SQS no entregó el mensaje propio enviado desde la otra EC2')
    return found


def main():
    folder, phase = Path(sys.argv[1]), sys.argv[2]
    config = json.loads((folder / 'connection.json').read_text())
    run_id = config['run_id']
    require(re.fullmatch('[0-9a-f]{24}', run_id), 'ID de sonda inválido')
    require(phase in ('seed', 'read-b-write', 'read-a', 'cleanup'), 'Fase inválida')
    name = 't06_probe_' + run_id
    owner = 't06:' + run_id
    connection = config['connection']
    session = boto3.Session(region_name=config['region'])
    require(session.get_credentials().method == 'iam-role', 'Se requieren credenciales del perfil EC2')
    sdk_config = Config(connect_timeout=5, read_timeout=15, retries={'mode': 'standard', 'max_attempts': 3})
    identity = session.client('sts', config=sdk_config).get_caller_identity()['Arn']
    require(':assumed-role/LabRole/' in identity, 'La llamada no usa LabRole')
    dynamo = session.client('dynamodb', config=sdk_config)
    sqs = session.client('sqs', config=sdk_config)
    cache = redis.Redis(host=connection['redis_host'], port=6379, socket_connect_timeout=5, socket_timeout=5, decode_responses=True)
    reader = redis.Redis(host=config['redis_reader_host'], port=6379, socket_connect_timeout=5, socket_timeout=5, decode_responses=True)
    mysql = pymysql.connect(host=connection['mysql_host'], user='catalog', password=connection['mysql_password'], database='catalogdb',
                            connect_timeout=5, read_timeout=10, write_timeout=10, ssl_ca=str(folder / 'rds-ca.pem'), ssl_verify_cert=True, ssl_verify_identity=True)
    postgres = psycopg.connect(host=connection['postgres_host'], user='orders', password=connection['postgres_password'], dbname='orders',
                               connect_timeout=5, sslmode='verify-full', sslrootcert=str(folder / 'rds-ca.pem'), options='-c statement_timeout=10000 -c lock_timeout=3000')
    table, queue = connection['dynamodb_table'], connection['sqs_queue_url']

    def row(db, key):
        with db.cursor() as cursor:
            cursor.execute(f'SELECT token FROM {name} WHERE id = %s', (key,))
            value = cursor.fetchone()
        db.commit()
        return value[0] if value else None

    def item(key):
        return dynamo.get_item(TableName=table, Key={'id': {'S': name + '-' + key}}, ConsistentRead=True).get('Item')

    checks = []
    try:
        if phase == 'seed':
            with mysql.cursor() as cursor:
                cursor.execute(f"CREATE TABLE {name} (id VARCHAR(8) PRIMARY KEY, token VARCHAR(64) NOT NULL) COMMENT = '{owner}'")
                cursor.execute(f'INSERT INTO {name} (id,token) VALUES (%s,%s)', ('a', run_id + ':a'))
            mysql.commit()
            with postgres.cursor() as cursor:
                cursor.execute(f'CREATE TABLE {name} (id VARCHAR(8) PRIMARY KEY, token VARCHAR(64) NOT NULL)')
                cursor.execute(f"COMMENT ON TABLE {name} IS '{owner}'")
                cursor.execute(f'INSERT INTO {name} (id,token) VALUES (%s,%s)', ('a', run_id + ':a'))
            postgres.commit()
            require(row(mysql, 'a') == row(postgres, 'a') == run_id + ':a', 'SQL no devolvió escritura A')
            require(cache.set(name + ':a', run_id + ':a', ex=600, nx=True), 'Clave Redis ya existía')
            dynamo.put_item(TableName=table, Item={'id': {'S': name + '-a'}, 'customerId': {'S': name}, 'token': {'S': run_id + ':a'}}, ConditionExpression='attribute_not_exists(id)')
            sqs.send_message(QueueUrl=queue, MessageBody=json.dumps({'t06_run': run_id, 'writer': 'a'}))
            checks = ['mysql-write-a', 'postgres-write-a', 'redis-write-a', 'dynamo-write-a', 'sqs-send-a']
        elif phase == 'read-b-write':
            for db in (mysql, postgres):
                require(row(db, 'a') == run_id + ':a', 'B no leyó fila SQL escrita por A')
                with db.cursor() as cursor:
                    cursor.execute(f'INSERT INTO {name} (id,token) VALUES (%s,%s)', ('b', run_id + ':b'))
                db.commit()
            require(cache.get(name + ':a') == run_id + ':a', 'B no leyó clave Redis de A')
            eventually(lambda: reader.get(name + ':a'), run_id + ':a')
            require(cache.set(name + ':b', run_id + ':b', ex=600, nx=True), 'Clave B ya existía')
            require(item('a')['token']['S'] == run_id + ':a', 'B no leyó ítem Dynamo de A')
            def index_has_a():
                result = dynamo.query(TableName=table, IndexName='idx_global_customerId', KeyConditionExpression='customerId = :c', ExpressionAttributeValues={':c': {'S': name}})['Items']
                return any(i['id']['S'] == name + '-a' for i in result)
            eventually(index_has_a, True)
            dynamo.put_item(TableName=table, Item={'id': {'S': name + '-b'}, 'customerId': {'S': name}, 'token': {'S': run_id + ':b'}}, ConditionExpression='attribute_not_exists(id)')
            receive_owned(sqs, queue, run_id, 'a')
            sqs.send_message(QueueUrl=queue, MessageBody=json.dumps({'t06_run': run_id, 'writer': 'b'}))
            checks = ['mysql-cross-a-b', 'postgres-cross-a-b', 'redis-primary-reader-cross-a-b', 'dynamo-gsi-cross-a-b', 'sqs-cross-a-b']
        elif phase == 'read-a':
            require(row(mysql, 'b') == row(postgres, 'b') == run_id + ':b', 'A no leyó escritura SQL de B')
            require(cache.get(name + ':b') == run_id + ':b', 'A no leyó Redis de B')
            eventually(lambda: reader.get(name + ':b'), run_id + ':b')
            require(item('b')['token']['S'] == run_id + ':b', 'A no leyó Dynamo de B')
            receive_owned(sqs, queue, run_id, 'b')
            checks = ['mysql-cross-b-a', 'postgres-cross-b-a', 'redis-replication-cross-b-a', 'dynamo-cross-b-a', 'sqs-cross-b-a']
        else:
            # El comentario identifica al dueño; no adoptar/borrar tablas ajenas.
            with mysql.cursor() as cursor:
                cursor.execute('SELECT TABLE_COMMENT FROM information_schema.tables WHERE table_schema = %s AND table_name = %s', ('catalogdb', name))
                value = cursor.fetchone()
                if value:
                    require(value[0] == owner, 'Tabla MySQL de otro dueño')
                    cursor.execute(f'DROP TABLE {name}')
            mysql.commit()
            with postgres.cursor() as cursor:
                cursor.execute("SELECT obj_description(to_regclass(%s), 'pg_class')", (name,))
                value = cursor.fetchone()[0]
                if value:
                    require(value == owner, 'Tabla PostgreSQL de otro dueño')
                    cursor.execute(f'DROP TABLE {name}')
            postgres.commit()
            for key in ('a', 'b'):
                value = cache.get(name + ':' + key)
                if value is not None:
                    require(value == run_id + ':' + key, 'Clave Redis de otro dueño')
                    cache.delete(name + ':' + key)
                value = item(key)
                if value:
                    require(value['customerId']['S'] == name, 'Ítem Dynamo de otro dueño')
                    dynamo.delete_item(TableName=table, Key={'id': {'S': name + '-' + key}}, ConditionExpression='customerId = :c', ExpressionAttributeValues={':c': {'S': name}})
                require(cache.get(name + ':' + key) is None and item(key) is None, 'Dato de sonda no eliminado')
            receive_owned(sqs, queue, run_id)
            with mysql.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s', ('catalogdb', name))
                require(cursor.fetchone()[0] == 0, 'Tabla MySQL no retirada')
            with postgres.cursor() as cursor:
                cursor.execute('SELECT to_regclass(%s)', (name,))
                require(cursor.fetchone()[0] is None, 'Tabla PostgreSQL no retirada')
            checks = ['sql-probe-tables-removed', 'redis-dynamo-probe-keys-removed', 'owned-sqs-messages-removed']
        print('T06_RESULT=' + json.dumps({'status': 'PASS', 'phase': phase, 'checks': checks, 'credential_method': 'iam-role', 'role': 'LabRole', 'sql_tls_verified': True}))
    finally:
        mysql.close()
        postgres.close()
        cache.close()
        reader.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Excepciones del driver pueden incluir DSN; no imprimir su texto/traceback.
        diagnostic = str(exc) if isinstance(exc, ProbeError) else type(exc).__name__
        print('T06_FAIL: ' + diagnostic, file=sys.stderr)
        sys.exit(1)
