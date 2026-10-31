import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
from acceso_kind import AccessError
spec = importlib.util.spec_from_file_location('alb_probe', Path(__file__).parents[1] / 'scripts/probar-alb.py')
alb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alb)


class ALBTests(unittest.TestCase):
    def test_missing_wrong_port_or_duplicate_targets_never_pass(self):
        ids = {'a': 'i-a', 'b': 'i-b'}
        descriptions = [{'Target': {'Id': value, 'Port': 8080}, 'TargetHealth': {'State': 'healthy'}} for value in ids.values()]
        self.assertEqual(alb.verify_target_set(descriptions, ids, 8080), {'a': 'healthy', 'b': 'healthy'})
        bad_port = copy.deepcopy(descriptions)
        bad_port[1]['Target']['Port'] = 30080
        for invalid in [descriptions[:1], descriptions + descriptions[:1], [descriptions[0], descriptions[0]], bad_port]:
            with self.subTest(invalid=invalid), self.assertRaises(AccessError):
                alb.verify_target_set(invalid, ids, 8080)

    def test_public_ec2_ingress_ssh_or_broad_alb_egress_fail(self):
        network = {'alb_security_group_id': 'sg-alb', 'application_security_group_id': 'sg-app'}
        public_http = {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}], 'Ipv6Ranges': [], 'UserIdGroupPairs': [], 'PrefixListIds': []}
        def referenced(group):
            return {'IpProtocol': 'tcp', 'FromPort': 8080, 'ToPort': 8080, 'IpRanges': [], 'Ipv6Ranges': [], 'UserIdGroupPairs': [{'GroupId': group, 'UserId': '123456789012'}], 'PrefixListIds': []}
        groups = {'sg-alb': {'GroupId': 'sg-alb', 'IpPermissions': [public_http], 'IpPermissionsEgress': [referenced('sg-app')]}, 'sg-app': {'GroupId': 'sg-app', 'IpPermissions': [referenced('sg-alb')]}}
        alb.verify_sg(groups, network, 8080)
        cases = []
        public_ec2 = copy.deepcopy(groups)
        public_ec2['sg-app']['IpPermissions'][0]['IpRanges'] = [{'CidrIp': '0.0.0.0/0'}]
        cases.append(public_ec2)
        ssh = copy.deepcopy(groups)
        ssh['sg-app']['IpPermissions'].append({'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22})
        cases.append(ssh)
        broad = copy.deepcopy(groups)
        broad['sg-alb']['IpPermissionsEgress'][0]['IpRanges'] = [{'CidrIp': '0.0.0.0/0'}]
        cases.append(broad)
        wrong_source = copy.deepcopy(groups)
        wrong_source['sg-app']['IpPermissions'][0]['UserIdGroupPairs'][0]['GroupId'] = 'sg-other'
        cases.append(wrong_source)
        for invalid in cases:
            with self.subTest(invalid=invalid), self.assertRaises(AccessError):
                alb.verify_sg(invalid, network, 8080)

    def test_http_200_from_another_run_does_not_prove_routing(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'a:previous-run'
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = response
        with patch.object(alb.urllib.request, 'build_opener', return_value=opener), self.assertRaises(AccessError):
            alb.sample_http('http://alb.example', 'current-run', {'a', 'b'})


if __name__ == '__main__':
    unittest.main()
