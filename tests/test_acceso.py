import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import acceso_kind as access


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'manifest.json'
        self.identity = {'pid': os.getpid(), 'start': access.process_start(os.getpid())}
        self.manifest = {'schema': 1, 'owner': self.identity, 'clusters': {}}
        for key, port in [('a', 16443), ('b', 26443)]:
            config = Path(self.folder.name) / (key + '.config')
            access.private_write(config, 'private')
            self.manifest['clusters'][key] = {
                'cluster_name': 'the-store-' + key, 'context': 'kind-the-store-' + key,
                'port': port, 'tunnel': self.identity, 'cluster_uid': 'uid-' + key,
                'instance_id': 'i-' + key, 'kubeconfig': str(config), 'provider_kubeconfig': str(config),
            }
        self.save()

    def save(self):
        access.private_write(self.path, json.dumps(self.manifest))

    def api(self, entry, *args):
        if args == ('get', '--raw', '/readyz'):
            return 'ok'
        if args[1] == 'namespace':
            return json.dumps({'metadata': {'uid': 'uid-' + entry['cluster_name'][-1]}})
        return json.dumps({'items': [{'metadata': {'name': entry['cluster_name'] + suffix}} for suffix in ('-control-plane', '-worker')]})

    def test_guard_rejects_swapped_context_dead_tunnel_and_identity_change(self):
        good = copy.deepcopy(self.manifest)
        with patch.object(access, 'inspect_config'), patch.object(access, 'kube', side_effect=self.api):
            self.assertEqual(access.validate_manifest(self.path)['uid_b'], 'uid-b')
            for key, field, bad in [('b', 'context', 'kind-the-store-a'), ('b', 'port', 16443), ('b', 'cluster_uid', 'uid-a'), ('b', 'instance_id', 'i-a'), ('b', 'tunnel', {'pid': os.getpid(), 'start': 'stale'})]:
                with self.subTest(field=field):
                    self.manifest = copy.deepcopy(good)
                    self.manifest['clusters'][key][field] = bad
                    self.save()
                    with self.assertRaises(access.AccessError):
                        access.validate_manifest(self.path)

    def test_private_files_and_stale_owner(self):
        self.path.chmod(0o644)
        with self.assertRaises(access.AccessError):
            access.validate_manifest(self.path)
        self.save()
        self.manifest['owner'] = {'pid': os.getpid(), 'start': 'old-session'}
        self.save()
        with self.assertRaises(access.AccessError):
            access.validate_manifest(self.path)
        link = self.path.parent / 'link'
        link.symlink_to(self.path)
        with self.assertRaises(access.AccessError):
            access.check_private(link)

    def test_kubeconfig_requires_tls_expected_endpoint_and_certificate_auth(self):
        config = {'clusters': [{'name': 'kind-the-store-a', 'cluster': {'server': 'https://127.0.0.1:16443', 'certificate-authority-data': 'ca'}}],
                  'contexts': [{'name': 'kind-the-store-a', 'context': {'cluster': 'kind-the-store-a', 'user': 'kind-the-store-a'}}],
                  'users': [{'name': 'kind-the-store-a', 'user': {'client-certificate-data': 'cert', 'client-key-data': 'key'}}]}
        for location, field, value in [('clusters', 'server', 'http://127.0.0.1:16443'), ('clusters', 'server', 'https://127.0.0.1:26443'), ('clusters', 'insecure-skip-tls-verify', True), ('clusters', 'proxy-url', 'http://proxy'), ('users', 'exec', {'command': 'aws'}), ('users', 'client-key-data', '')]:
            bad = copy.deepcopy(config)
            bad[location][0]['cluster' if location == 'clusters' else 'user'][field] = value
            with self.subTest(field=field), patch.object(access, 'invoke', return_value=json.dumps(bad)):
                with self.assertRaises(access.AccessError):
                    access.inspect_config(self.path, 'kind-the-store-a', 16443)
        with patch.object(access, 'invoke', return_value=json.dumps(config)):
            access.inspect_config(self.path, 'kind-the-store-a', 16443)

    def test_command_failure_never_displays_private_output(self):
        with patch.object(access.subprocess, 'run', return_value=subprocess.CompletedProcess(['kubectl'], 1, 'SECRET_KEY', 'SECRET_KEY')):
            with self.assertRaises(access.AccessError) as error:
                access.invoke(['kubectl'])
        self.assertNotIn('SECRET_KEY', str(error.exception))

    def test_cleanup_deletes_private_material_even_if_remote_cleanup_fails(self):
        session = access.AccessSession()
        session.folder = tempfile.TemporaryDirectory(dir=self.folder.name)
        secret = Path(session.folder.name) / 'private'
        secret.write_text('SECRET')
        log = Path(session.folder.name) / 'log'
        log.write_text('Starting session with SessionId: owned-session\n')
        session.logs = [log]
        session.region = 'us-east-1'
        with patch.object(access, 'aws', side_effect=RuntimeError('expired')) as aws:
            with self.assertRaises(access.AccessError):
                session.close()
            self.assertEqual(json.loads(aws.call_args.args[-1]), [{'key': 'SessionId', 'value': 'owned-session'}])
        self.assertFalse(secret.exists())
        session.close()  # limpieza idempotente

    def test_invalid_manifest_external_and_exec_are_secret_free(self):
        for script, extra, stdin in [('validar-acceso.py', [], json.dumps({'manifest': str(self.path) + '-missing'})), ('credencial-kind.py', [str(self.path) + '-missing', 'a'], '')]:
            result = subprocess.run([sys.executable, str(access.ROOT / 'scripts' / script), *extra], input=stdin, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, '')
            self.assertIn('Acceso kind inválido', result.stderr)

    def test_wrapper_explains_lost_access_when_provider_hides_plugin_stderr(self):
        spec = importlib.util.spec_from_file_location('access_cli', access.ROOT / 'scripts/acceso.py')
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        with patch.object(sys, 'argv', ['acceso.py', 'run', '--', 'terraform', 'apply', 'saved.tfplan']), patch.object(cli.shutil, 'which', return_value='/bin/tool'), patch.object(cli.signal, 'signal'), patch.object(cli, 'AccessSession') as session, patch.object(cli.subprocess, 'Popen') as process, patch.object(cli, 'validate_manifest', side_effect=access.AccessError('Falta un túnel propio activo')), patch.object(sys, 'stderr', new_callable=io.StringIO) as stderr:
            session.return_value.__enter__.return_value.manifest_path = self.path
            process.return_value.wait.return_value = 1
            process.return_value.poll.return_value = 1
            self.assertEqual(cli.main(), 1)
            self.assertIn('Falta un túnel propio activo', stderr.getvalue())
            session.return_value.__exit__.assert_called_once()


if __name__ == '__main__':
    unittest.main()
