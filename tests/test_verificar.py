import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import json

spec = importlib.util.spec_from_file_location('verificar', Path(__file__).parents[1] / 'scripts/verificar.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class VerificationTests(unittest.TestCase):
    def test_dns_exec_and_http_errors_never_count_as_network_block(self):
        for code, output in ((6, '000'), (7, '000'), (126, ''), (127, ''), (1, ''), (28, ''), (0, '200')):
            with self.subTest(code=code, output=output), self.assertRaises(v.CheckError):
                v.curl_result(subprocess.CompletedProcess([], code, output), blocked=True)
        v.curl_result(subprocess.CompletedProcess([], 28, '000'), blocked=True)

    def test_connection_requires_http_response(self):
        v.curl_result(subprocess.CompletedProcess([], 0, '404'))
        for code in (6, 7, 28, 127):
            with self.assertRaises(v.CheckError):
                v.curl_result(subprocess.CompletedProcess([], code, '000'))

    def test_running_without_readiness_and_extra_pods_fail(self):
        pod = {'metadata': {}, 'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'False'}]}}
        self.assertFalse(v.ready([pod], 1))
        pod['status']['conditions'][0]['status'] = 'True'
        self.assertTrue(v.ready([pod], 1))
        self.assertFalse(v.ready([pod, pod], 1))

    def test_rollback_rejects_wrong_image_and_quarantine_rejects_restarts(self):
        base = {'a': {'cluster_uid': 'one', 'pods': {'p': {'restartCount': 0}}, 'images': {'ui': ['v1']}, 'runtime_images': {'ui': ['sha256:one']}}}
        changed = json.loads(json.dumps(base)); changed['a']['pods']['p']['restartCount'] = 1
        with self.assertRaises(v.CheckError):
            v.compare_snapshots(base, changed, 'unchanged')
        changed['a']['images']['ui'] = ['v2']
        with self.assertRaises(v.CheckError):
            v.compare_snapshots(base, changed, 'rollback')

    def test_inaccessible_api_stops_before_negative_probe(self):
        c = v.Cluster({'kubeconfig': 'missing', 'context': 'a'}, 'the-store')
        with patch.object(v, 'command', side_effect=v.CheckError('API inaccesible')):
            with self.assertRaises(v.CheckError):
                c.bootstrap()

    def test_failed_probe_is_registered_for_cleanup(self):
        c = v.Cluster({'kubeconfig': 'x', 'context': 'a'}, 'the-store')
        with patch.object(c, 'get', return_value={'spec': {'template': {'spec': {'containers': [{'image': 'ui@sha256:123'}]}}}}), patch.object(c, 'run', side_effect=[None, v.CheckError('ImagePullBackOff')]):
            with self.assertRaises(v.CheckError):
                c.stranger()
        self.assertEqual(len(c.created), 1)
        with patch.object(c, 'run') as run:
            c.cleanup()
            self.assertIn(c.created[0], run.call_args.args)

    def test_checkout_uses_node_loopback_and_every_pod_ip(self):
        c = v.Cluster({'kubeconfig': 'x', 'context': 'a'}, 'the-store')
        def pod(ip):
            return {'metadata': {}, 'status': {'podIP': ip, 'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]}}
        with patch.object(c, 'pod', return_value='checkout-1'), patch.object(c, 'get', return_value={'items': [pod('10.0.0.1'), pod('10.0.0.2')]}), patch.object(c, 'node_http', side_effect=[{'status': 'ok', 'code': 200}, {'status': 'timeout'}, {'status': 'timeout'}]) as node:
            c.http_probe('checkout', 'orders', blocked=True)
            urls = [call.args[1] for call in node.call_args_list]
            self.assertEqual(urls, ['http://127.0.0.1:8080/health', 'http://10.0.0.1:8080/actuator/health/readiness', 'http://10.0.0.2:8080/actuator/health/readiness'])

    def test_no_destination_pods_or_node_errors_are_not_blocks(self):
        c = v.Cluster({'kubeconfig': 'x', 'context': 'a'}, 'the-store')
        with patch.object(c, 'get', return_value={'items': []}), self.assertRaises(v.CheckError):
            c.targets('orders')
        for response in ({'status': 'error'}, {'status': 'ok', 'code': 200}, {}):
            with patch.object(c, 'node_http', return_value=response), self.assertRaises(v.CheckError):
                c.probe_from('checkout', 'checkout', 'http://10.0.0.1:8080', True)

    def test_targets_include_running_pod_without_readiness(self):
        c = v.Cluster({'kubeconfig': 'x', 'context': 'a'}, 'the-store')
        pod = {'metadata': {}, 'status': {'podIP': '10.0.0.3', 'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'False'}]}}
        with patch.object(c, 'get', return_value={'items': [pod]}):
            self.assertEqual(c.targets('orders'), ['10.0.0.3'])

    def test_node_http_enforces_status_and_json(self):
        import http.server
        import threading
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(500 if self.path == '/bad-status' else 200)
                self.end_headers()
                self.wfile.write(b'bad' if self.path == '/bad-json' else b'[]')
            def log_message(self, *args): pass
        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            url = 'http://127.0.0.1:' + str(server.server_port)
            for path, expected in (('/', 'ok'), ('/bad-status', 'error'), ('/bad-json', 'error')):
                result = subprocess.run(['node', '-e', v.NODE_HTTP, url + path, 'json'], capture_output=True, text=True, timeout=8, check=True)
                self.assertEqual(json.loads(result.stdout)['status'], expected)
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_bootstrap_needs_no_application_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'; report = Path(tmp) / 'report.json'
            config.write_text(json.dumps({'clusters': {k: {'kubeconfig': k, 'context': k} for k in ('a','b')}}))
            with patch('sys.argv', ['verificar', '--config', str(config), '--mode', 'bootstrap', '--report', str(report)]), patch.object(v.shutil, 'which', return_value='/tool'), patch.object(v.Cluster, 'bootstrap', lambda c: c.spec['context']), patch.object(v.Cluster, 'snapshot', side_effect=AssertionError('No hay app')) as snapshot:
                self.assertEqual(v.main(), 0)
                snapshot.assert_not_called()
            self.assertEqual(json.loads(report.read_text())['status'], 'PASS')

    def test_duplicate_apis_abort_before_application_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            config=Path(tmp)/'config.json'; report=Path(tmp)/'report.json'
            config.write_text(json.dumps({'region':'us-east-1', 'alb':{'url':'http://alb','target_group_arn':'arn','instance_ids':['i-a','i-b']},'clusters':{k:{'kubeconfig':k,'context':k,'url':'http://'+k} for k in ('a','b')}}))
            with patch('sys.argv',['verificar','--config',str(config),'--mode','app','--report',str(report)]), patch.object(v.shutil,'which',return_value='/tool'), patch.object(v.Cluster,'bootstrap',return_value='same'), patch.object(v.Cluster,'application') as application:
                self.assertEqual(v.main(),1)
                application.assert_not_called()

    def test_snapshot_excludes_own_probes(self):
        c = v.Cluster({'kubeconfig':'a','context':'a'}, 'the-store')
        ui = {'metadata': {'name':'ui-1','uid':'uid-1','labels':{'app':'ui'}}, 'status':{}}
        probe = {'metadata': {'name':'probe-1','uid':'uid-p','labels':{'probe':'probe-1'}}, 'status':{}}
        deployment = {'metadata':{'name':'ui'}, 'spec':{'template':{'spec':{'containers':[{'image':'ui@sha256:one'}]}}}}
        with patch.object(c, 'get', side_effect=[{'items':[ui,probe]}, {'items':[deployment]}, {'metadata':{'uid':'cluster'}}]):
            self.assertEqual(set(c.snapshot()['pods']), {'ui-1'})

    def test_sqs_event_requires_exact_new_order(self):
        self.assertEqual(v.event_order({'Body': '{"order":{"id":"new"}}'}), 'new')
        self.assertEqual(v.event_order({'Body': '{"id":"new"}'}), 'new')
        self.assertEqual(v.event_order({'Body': '{"Message":"{\\"id\\":\\"new\\"}"}'}), 'new')
        self.assertNotEqual(v.event_order({'Body': '{"id":"old"}'}), 'new')

    def test_sqs_observation_restores_messages_without_deleting(self):
        message = {'MessageId':'message', 'ReceiptHandle':'receipt', 'Body':'{"order":{"id":"new"}}'}
        with patch.object(v, 'aws', side_effect=[{'Messages':[message]}, {}]) as aws:
            self.assertTrue(v.observe_order_event({'queue_url':'queue'}, 'new'))
            self.assertEqual(aws.call_args.args[2], 'change-message-visibility')
            self.assertNotIn('delete-message', str(aws.call_args_list))

    def test_sqs_observation_accepts_empty_successful_visibility_response(self):
        received = json.dumps({'Messages': [{'MessageId': 'message', 'ReceiptHandle': 'receipt', 'Body': '{"order":{"id":"new"}}'}]})
        for empty in ('', '\n'):
            with self.subTest(output=repr(empty)), patch.object(v, 'command', side_effect=[subprocess.CompletedProcess([], 0, received), subprocess.CompletedProcess([], 0, empty)]) as command:
                self.assertTrue(v.observe_order_event({'region': 'us-east-1', 'queue_url': 'queue'}, 'new'))
                self.assertIn('change-message-visibility', command.call_args.args[0])

    def test_nonempty_malformed_aws_response_still_fails(self):
        with patch.object(v, 'command', return_value=subprocess.CompletedProcess([], 0, 'not-json')):
            with self.assertRaises(json.JSONDecodeError):
                v.aws({'region': 'us-east-1'}, 'sqs', 'receive-message')

    def test_duplicate_clusters_and_missing_tools_fail_with_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'config.json'; report = Path(tmp) / 'report.json'
            config.write_text(json.dumps({'clusters': {'a': {}, 'b': {}}}))
            with patch('sys.argv', ['verificar', '--config', str(config), '--mode', 'bootstrap', '--report', str(report)]), patch.object(v.shutil, 'which', return_value=None):
                self.assertEqual(v.main(), 1)
            self.assertEqual(json.loads(report.read_text())['status'], 'FAIL')
        base = {'a': {'cluster_uid': 'same', 'pods': {}, 'images': {}}}
        changed = {'a': {'cluster_uid': 'different', 'pods': {}, 'images': {}}}
        with self.assertRaises(v.CheckError):
            v.compare_snapshots(base, changed, 'unchanged')


if __name__ == '__main__':
    unittest.main()
