import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import ssm
spec = importlib.util.spec_from_file_location('verify_compute', Path(__file__).parents[1] / 'scripts/verificar-computo.py')
c = importlib.util.module_from_spec(spec); spec.loader.exec_module(c)


class SSMTests(unittest.TestCase):
    def test_notfound_and_denied_remain_distinct_without_printing_error_details(self):
        for code in ('InvalidVolume.NotFound', 'InvalidAllocationID.NotFound', 'AccessDenied'):
            failure = subprocess.CompletedProcess([], 1, '', f'An error occurred ({code}) when calling Describe: SECRET_DETAILS')
            with self.subTest(code=code), patch.object(ssm.subprocess, 'run', return_value=failure):
                with self.assertRaises(ssm.SSMError) as error:
                    ssm.aws('us-east-1', 'ec2', 'describe-volumes')
                self.assertEqual(str(error.exception), code)

    def test_success_parent_with_nonzero_plugin_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ssm, 'aws', side_effect=[{'Command': {'CommandId': 'own'}}, {'Status': 'Success', 'ResponseCode': 1, 'StandardOutputContent': 'failed'}]):
            with self.assertRaises(ssm.SSMError):
                ssm.run('us-east-1', 'i-own', 'false', Path(tmp) / 'log')

    def test_interrupted_poll_cancels_only_owned_command(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(ssm, 'aws', side_effect=[{'Command': {'CommandId': 'own'}}, KeyboardInterrupt(), {}]) as aws:
            with self.assertRaises(KeyboardInterrupt):
                ssm.run('us-east-1', 'i-own', 'true', Path(tmp) / 'log')
            self.assertEqual(aws.call_args.args, ('us-east-1', 'ssm', 'cancel-command', '--command-id', 'own', '--instance-ids', 'i-own'))

    def test_missing_or_truncated_summary_fails(self):
        for text in ('', 'PASS', 'T03_RESULT={'):
            with self.assertRaises((ssm.SSMError, ValueError)):
                c.parse_summary(text)
        result = {'status':'PASS','node_uids':{'a':'1','b':'2'},'container_ids':['1','2'],'memory_kib':8_000_000}
        self.assertEqual(c.parse_summary('other log\nT03_RESULT=' + json.dumps(result)), result)
        result['node_uids'].pop('b')
        with self.assertRaises(ssm.SSMError):
            c.parse_summary('T03_RESULT=' + json.dumps(result))


if __name__ == '__main__':
    unittest.main()
