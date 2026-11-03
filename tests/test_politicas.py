"""Regression checks for evidence: timeout is the only accepted negative."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('politicas', ROOT / 'scripts/probar-politicas.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class EvidenceTests(unittest.TestCase):
    def test_no_other_error_counts_as_isolation(self):
        for status in ({'status': 'error', 'code': 'ECONNREFUSED'},
                       {'status': 'error', 'code': 'ENOTFOUND'},
                       {'status': 'ok'}, {}, None):
            with self.subTest(status=status), self.assertRaises(probe.CheckError):
                probe.check_probe(status, True)
        probe.check_probe({'status': 'timeout'}, True)

    def test_positive_requires_success(self):
        for status in ({'status': 'timeout'}, {'status': 'error'}):
            with self.assertRaises(probe.CheckError):
                probe.check_probe(status, False)
        probe.check_probe({'status': 'ok'}, False)

    def test_restart_and_template_change_fail_comparison(self):
        original = {'cluster_uid': 'a', 'pods': {'pod': {'uid': 'u', 'restarts': 0}}, 'images': {}, 'templates': {'checkout': 'stable'}}
        for field, value in [('cluster_uid', 'b'), ('pods', {'pod': {'uid': 'u', 'restarts': 1}}), ('templates', {'checkout': 'changed'})]:
            changed = dict(original, **{field: value})
            with self.subTest(field=field), self.assertRaises(probe.CheckError):
                probe.compare(original, changed)

    def test_node_probe_connection_refused_is_not_timeout(self):
        # Closed loopback port is a real socket error, not mocked isolation.
        import socket
        with socket.socket() as held:
            held.bind(('127.0.0.1', 0))
            port = held.getsockname()[1]
            result = subprocess.run(['node', '-e', probe.NODE_PROBE, 'tcp', '127.0.0.1', str(port)], capture_output=True, text=True, check=True, timeout=10)
        value = json.loads(result.stdout)
        self.assertEqual(value, {'status': 'error', 'code': 'ECONNREFUSED'})
        with self.assertRaises(probe.CheckError):
            probe.check_probe(value, True)

class PlanTests(unittest.TestCase):
    def test_transition_requires_policies_only(self):
        plan_spec = importlib.util.spec_from_file_location('plan_politicas', ROOT / 'scripts/validar-plan-politicas.py')
        module = importlib.util.module_from_spec(plan_spec)
        plan_spec.loader.exec_module(module)
        def plan(resource_type, actions):
            return {'resource_changes': [{'type': resource_type, 'change': {'actions': actions}}]}
        self.assertEqual(module.validate(plan('kubernetes_network_policy_v1', ['delete'])), 1)
        for value in [plan('kubernetes_deployment_v1', ['update']), plan('kubernetes_service_v1', ['delete', 'create']), plan('kubernetes_network_policy_v1', ['no-op']), plan('kubernetes_network_policy_v1', ['create', 'delete'])]:
            with self.assertRaises(ValueError):
                module.validate(value)


class AdditivePolicyTests(unittest.TestCase):
    def test_unmanaged_or_broadened_allow_is_rejected(self):
        expected = probe.expected_policies('quarantine', [], '10.244.0.0/16', '172.20.0.0/16')
        actual = [{'metadata': {'name': name}, 'spec': value} for name, value in expected.items()]
        probe.validate_policies(actual, expected)
        extra = {'metadata': {'name': 'allow-all'}, 'spec': {'podSelector': {}, 'ingress': [{}]}}
        with self.assertRaises(probe.CheckError):
            probe.validate_policies(actual + [extra], expected)
        broadened = json.loads(json.dumps(actual))
        external = next(p for p in broadened if p['metadata']['name'] == 'allow-ui-external')
        external['spec']['egress'][0]['to'][0]['ipBlock'].pop('except')
        with self.assertRaises(probe.CheckError):
            probe.validate_policies(broadened, expected)

class CheckoutHttpTests(unittest.TestCase):
    """Use the real Node HTTP client, with no curl in the simulated pod."""
    def node_cluster(self):
        class NodeOnly:
            def execute(inner, pod, *args, timeout=15, **kwargs):
                self.assertEqual(args[0], 'node')
                return subprocess.run(args, capture_output=True, text=True, check=True, timeout=timeout)
        return NodeOnly()

    def test_checkout_health_uses_node_and_requires_http_200(self):
        import http.server
        import threading
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200 if self.path == '/health' else 503)
                self.send_header('Content-Length', '0')
                self.end_headers()
            def log_message(self, *args):
                pass
        with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
            pod = {'metadata': {'name': 'checkout-real', 'labels': {'app': 'checkout'}}}
            url = 'http://127.0.0.1:' + str(server.server_port)
            try:
                probe.http_probe(self.node_cluster(), pod, url + '/health')
                for blocked in (False, True):
                    with self.subTest(blocked=blocked), self.assertRaises(probe.CheckError):
                        probe.http_probe(self.node_cluster(), pod, url + '/unhealthy', blocked)
            finally:
                server.shutdown();thread.join(timeout=5)

    def test_checkout_refused_connection_cannot_pass_isolation(self):
        import socket
        with socket.socket() as held:
            held.bind(('127.0.0.1', 0))
            target = 'http://127.0.0.1:' + str(held.getsockname()[1]) + '/health'
            pod = {'metadata': {'name': 'checkout-real', 'labels': {'app': 'checkout'}}}
            with self.assertRaises(probe.CheckError):
                probe.http_probe(self.node_cluster(), pod, target, True)

class FunctionalCleanupTests(unittest.TestCase):
    def test_failed_cart_assertion_still_removes_owned_data(self):
        from unittest.mock import patch
        calls = []
        def api(cluster, pod, method, url, body=None):
            calls.append((method, url))
            if url == 'http://catalog/catalog/products':
                return [{'id': 'product', 'price': 123}]
            if method == 'GET':
                return []
            return None
        evidence = {}
        with patch.object(probe, 'json_api', side_effect=api), self.assertRaises(probe.CheckError):
            probe.functional_controls(None, 'ui-pod', evidence)
        self.assertEqual(calls[-1], ('DELETE', 'http://carts/carts/' + evidence['functional_customer']))
        self.assertTrue(evidence['functional_cleanup'])


if __name__ == '__main__':
    unittest.main()
