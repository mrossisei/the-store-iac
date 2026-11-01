import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from acceso_kind import AccessError
import datos_topologia
from datos_topologia import check_data_sg, check_rds, redis_version_matches


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


driver = load('data_driver', 'scripts/probar-datos.py')
# Los tests del protocolo SQS no necesitan instalar drivers SQL en el operador.
with patch.dict(sys.modules, {name: MagicMock() for name in ('boto3', 'botocore', 'botocore.config', 'pymysql', 'psycopg', 'redis')}):
    client = load('data_client', 'scripts/probes/datos.py')


class DataTests(unittest.TestCase):
    def test_available_without_standby_waits_for_aws_and_keeps_failure_on_timeout(self):
        first = {'DBInstanceStatus': 'available', 'MultiAZ': True}
        ready = dict(first, SecondaryAvailabilityZone='us-east-1b')
        with patch.object(datos_topologia, 'aws', side_effect=[{'DBInstances': [first]}, {'DBInstances': [ready]}]), patch.object(datos_topologia.time, 'sleep'), patch.object(datos_topologia.time, 'monotonic', return_value=0):
            self.assertEqual(datos_topologia.ready_rds('region', 'own'), ready)
        with patch.object(datos_topologia, 'aws', return_value={'DBInstances': [first]}), patch.object(datos_topologia.time, 'monotonic', side_effect=[0, 901]):
            self.assertNotIn('SecondaryAvailabilityZone', datos_topologia.ready_rds('region', 'own'))

    def test_private_config_cannot_use_legacy_or_unencrypted_backend(self):
        metadata = {'backend': {'type': 's3', 'config': {'key': 'kind/infra', 'bucket': 'private-state', 'encrypt': True, 'use_lockfile': True}}}
        self.assertEqual(driver.backend_bucket(metadata, 'kind/infra'), 'private-state')
        for field, value in [('key', 'legacy.tfstate'), ('encrypt', False), ('use_lockfile', False)]:
            bad = copy.deepcopy(metadata)
            bad['backend']['config'][field] = value
            with self.subTest(field=field), self.assertRaises(AccessError):
                driver.backend_bucket(bad, 'kind/infra')

    def test_redis_patch_is_allowed_without_accepting_another_minor(self):
        self.assertTrue(redis_version_matches('7.1.0', '7.1'))
        self.assertTrue(redis_version_matches('7.1', '7.1'))
        self.assertFalse(redis_version_matches('7.10', '7.1'))
        self.assertFalse(redis_version_matches('7.2.0', '7.1'))

    def test_rds_available_alone_does_not_prove_multi_az_or_private_storage(self):
        db = {'DBInstanceStatus': 'available', 'Engine': 'postgres', 'EngineVersion': '17.11', 'MultiAZ': True,
              'AvailabilityZone': 'us-east-1a', 'SecondaryAvailabilityZone': 'us-east-1b',
              'PubliclyAccessible': False, 'DBInstanceClass': 'db.t3.micro', 'StorageType': 'gp2', 'AllocatedStorage': 20,
              'StorageEncrypted': True, 'MonitoringInterval': 0,
              'DBSubnetGroup': {'VpcId': 'vpc-own', 'Subnets': [{'SubnetIdentifier': 's-a'}, {'SubnetIdentifier': 's-b'}]},
              'VpcSecurityGroups': [{'VpcSecurityGroupId': 'sg-data', 'Status': 'active'}]}
        expected = dict(engine='postgres', version='17.11', vpc='vpc-own', subnets=['s-a', 's-b'], security_group='sg-data', zones=['us-east-1a', 'us-east-1b'], instance_class='db.t3.micro')
        check_rds(db, **expected)
        for field, value in [('MultiAZ', False), ('SecondaryAvailabilityZone', 'us-east-1a'), ('PubliclyAccessible', True), ('StorageType', 'gp3'), ('AllocatedStorage', 101), ('MonitoringInterval', 60)]:
            bad = copy.deepcopy(db)
            bad[field] = value
            with self.subTest(field=field), self.assertRaises(AccessError):
                check_rds(bad, **expected)

    def test_data_ports_cannot_be_opened_to_cidr_or_another_sg(self):
        rules = [{'IpProtocol': 'tcp', 'FromPort': port, 'ToPort': port, 'IpRanges': [], 'UserIdGroupPairs': [{'GroupId': 'sg-app'}]} for port in (3306, 5432, 6379)]
        check_data_sg({'IpPermissions': rules}, 'sg-app')
        for source in ('public', 'other'):
            bad = copy.deepcopy(rules)
            if source == 'public':
                bad[0]['IpRanges'] = [{'CidrIp': '10.0.0.0/16'}]
            else:
                bad[0]['UserIdGroupPairs'][0]['GroupId'] = 'sg-other'
            with self.subTest(source=source), self.assertRaises(AccessError):
                check_data_sg({'IpPermissions': bad}, 'sg-app')

    def test_partial_or_repeated_remote_result_cannot_pass(self):
        value = {'status': 'PASS', 'phase': 'cleanup', 'role': 'LabRole', 'credential_method': 'iam-role', 'sql_tls_verified': True,
                 'checks': ['sql-probe-tables-removed', 'redis-dynamo-probe-keys-removed', 'owned-sqs-messages-removed']}
        line = 'T06_RESULT=' + json.dumps(value)
        driver.parse_result(line, 'cleanup')
        for bad in (line + '\n' + line, line.replace('iam-role', 'env'), line.replace('true', 'false'), 'T06_RESULT=' + json.dumps(dict(value, checks=['sql-probe-tables-removed']))):
            with self.assertRaises(AccessError):
                driver.parse_result(bad, 'cleanup')

    def test_sqs_restores_foreign_messages_and_deletes_only_matching_run(self):
        sqs = MagicMock()
        sqs.receive_message.return_value = {'Messages': [
            {'Body': 'not-json', 'ReceiptHandle': 'foreign-1'},
            {'Body': json.dumps({'t06_run': 'old', 'writer': 'a'}), 'ReceiptHandle': 'foreign-2'},
            {'Body': json.dumps({'t06_run': 'own', 'writer': 'a'}), 'ReceiptHandle': 'own-receipt'},
        ]}
        self.assertTrue(client.receive_owned(sqs, 'queue', 'own', 'a'))
        sqs.delete_message.assert_called_once_with(QueueUrl='queue', ReceiptHandle='own-receipt')
        self.assertEqual(sqs.change_message_visibility.call_count, 2)
        self.assertTrue(all(call.kwargs['VisibilityTimeout'] == 0 for call in sqs.change_message_visibility.call_args_list))

    def test_empty_sqs_does_not_count_as_successful_delivery(self):
        with patch.object(client.time, 'monotonic', side_effect=[0, 46]):
            with self.assertRaises(client.ProbeError):
                client.receive_owned(MagicMock(), 'queue', 'own', 'a')

    def test_wrong_phase_restores_visibility_before_failure(self):
        sqs = MagicMock()
        sqs.receive_message.return_value = {'Messages': [{'Body': json.dumps({'t06_run': 'own', 'writer': 'b'}), 'ReceiptHandle': 'unexpected'}]}
        with self.assertRaises(client.ProbeError):
            client.receive_owned(sqs, 'queue', 'own', 'a')
        sqs.delete_message.assert_not_called()
        sqs.change_message_visibility.assert_called_once_with(QueueUrl='queue', ReceiptHandle='unexpected', VisibilityTimeout=0)

    def test_lost_upload_response_still_removes_exact_private_versions_only(self):
        key = 'scratch/t06/own/connection.json'
        foreign = {'Key': key + '-foreign', 'VersionId': 'foreign-version'}
        listing = {'Versions': [{'Key': key, 'VersionId': 'own-version'}, foreign], 'DeleteMarkers': [{'Key': key, 'VersionId': 'own-marker'}]}
        with patch.object(driver, 'aws', side_effect=[listing, {}, {}, {'Versions': [foreign]}]) as aws:
            driver.remove_config_versions('us-east-1', 'bucket', key, 'account')
        deletes = [call.args for call in aws.call_args_list if call.args[2] == 'delete-object']
        self.assertEqual(len(deletes), 2)
        self.assertTrue(all(call[call.index('--key') + 1] == key for call in deletes))
        self.assertNotIn('foreign-version', str(deletes))

    def test_private_object_version_remaining_cannot_be_reported_clean(self):
        key = 'scratch/t06/own/connection.json'
        with patch.object(driver, 'aws', side_effect=[{}, {'Versions': [{'Key': key, 'VersionId': 'left'}]}]):
            with self.assertRaises(AccessError):
                driver.remove_config_versions('us-east-1', 'bucket', key, 'account')


if __name__ == '__main__':
    unittest.main()
