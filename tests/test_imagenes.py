import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

pub = load('pub', 'publicar-imagenes.py')
pull = load('pull', 'probar-pull-imagenes.py')


class Releases(unittest.TestCase):
    def setUp(self):
        self.repos = {s: '891200271122.dkr.ecr.us-east-1.amazonaws.com/the-store/' + s for s in pub.SERVICES}
        self.images = {s: dict(repository=r, digest='sha256:' + 'a' * 64, platform='linux/amd64') for s, r in self.repos.items()}
        self.manifest = dict(schema=1, region='us-east-1', versions=dict(v1=self.images, v2=copy.deepcopy(self.images)))

    @patch.object(pub, 'description', return_value={'imageDigest': 'sha256:' + 'a' * 64})
    def test_select_v1_v2_v1_only_reads_registry(self, describe):
        with patch.object(pub, 'command', side_effect=AssertionError('No docker/build/push allowed')):
            for v in ('v1', 'v2', 'v1'):
                result = pub.validate(self.manifest, v, self.repos)
                self.assertEqual(len(result), 5)
                self.assertTrue(all('@sha256:' in r for r in result.values()))
        self.assertEqual(describe.call_count, 15)

    def test_missing_service_and_wrong_platform_rejected(self):
        del self.images['carts']
        with self.assertRaisesRegex(ValueError, 'incompleta'):
            pub.validate(self.manifest, 'v1', self.repos)
        self.images['carts'] = dict(repository=self.repos['carts'], digest='sha256:' + 'a' * 64, platform='linux/arm64')
        with patch.object(pub, 'description', return_value={'imageDigest': 'sha256:' + 'a' * 64}):
            with self.assertRaisesRegex(ValueError, 'inválida'):
                pub.validate(self.manifest, 'v1', self.repos)

    @patch.object(pub, 'description', return_value={'imageDigest': 'sha256:' + 'b' * 64})
    def test_wrong_digest_rejected(self, _):
        with self.assertRaisesRegex(ValueError, 'Digest incorrecto'):
            pub.validate(self.manifest, 'v1', self.repos)

    def test_existing_version_rejected_before_build(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'manifest.json'
            pub.save(path, self.manifest)
            with patch.object(pub, 'repositories', return_value=self.repos), patch.object(pub, 'docker_login', side_effect=AssertionError):
                with self.assertRaisesRegex(ValueError, 'ya publicada'):
                    pub.publish(path, 'v1')

    def test_unrecorded_remote_tag_rejected_even_resume(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(pub, 'repositories', return_value=self.repos), patch.object(pub, 'aws', return_value={'repositories': [{'imageTagMutability': 'IMMUTABLE'}]}), patch.object(pub, 'description', return_value={'imageDigest': 'sha256:' + 'a' * 64}):
                with self.assertRaisesRegex(ValueError, 'Reescritura'):
                    pub.publish(Path(d) / 'manifest.json', 'v1', resume=True)

    def test_only_one_or_two_builds(self):
        with self.assertRaisesRegex(ValueError, 'Máximo dos'):
            pub.publish(Path('/unused'), 'v1', jobs=3)

    def test_hosts_require_distinct_ids_and_ready(self):
        coord = dict(schema=1, region='us-east-1', status='ready', compute=dict(instance_ids=dict(a='i-12345678', b='i-abcdef12')))
        self.assertEqual(set(pull.instance_ids(coord)), {'a', 'b'})
        nested = dict(schema=1, status='hosts_ready', region='us-east-1', compute={k: {'instance_id': v} for k, v in coord['compute']['instance_ids'].items()})
        self.assertEqual(pull.instance_ids(nested), coord['compute']['instance_ids'])
        coord['compute']['instance_ids']['b'] = 'i-12345678'
        with self.assertRaises(ValueError):
            pull.instance_ids(coord)
        coord['status'] = 'preparing'
        with self.assertRaises(ValueError):
            pull.instance_ids(coord)

    def test_generation_change_or_preparing_blocks_run_command(self):
        import json
        expected = dict(schema=1, generation=2, status='hosts_ready', region='us-east-1', compute=dict(a='i-12345678', b='i-abcdef12'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'coordination.json'
            path.write_text(json.dumps(expected))
            self.assertEqual(set(pull.ensure_current(path, expected)), {'a', 'b'})
            current = dict(expected, generation=3)
            path.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError, 'generación'):
                pull.ensure_current(path, expected)
            current = dict(expected, status='preparing')
            path.write_text(json.dumps(current))
            with self.assertRaisesRegex(ValueError, 'no lista'):
                pull.ensure_current(path, expected)

    def test_remote_script_isolated_and_has_no_workload_actions(self):
        script = pull.host_script({'v1': {}, 'v2': {}})
        self.assertIn('env -i', script)
        self.assertIn('assumed-role/LabRole/', script)
        self.assertIn("AWS_SHARED_CREDENTIALS_FILE='/dev/null'", script)
        self.assertNotIn('kubectl', script)
        self.assertNotIn('kind ', script)
        compile(script.split("<<'T07PY'\n", 1)[1].rsplit('\nT07PY', 1)[0], '<host>', 'exec')


if __name__ == '__main__':
    unittest.main()
