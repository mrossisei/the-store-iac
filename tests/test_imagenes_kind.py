import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
import urllib.error
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('kind_images', Path(__file__).parents[1] / 'scripts/probes/imagenes_kind.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ImageCacheTests(unittest.TestCase):
    def test_blob_redirect_does_not_forward_registry_authorization(self):
        content = b'valid blob'
        digest = 'sha256:' + hashlib.sha256(content).hexdigest()
        redirect = urllib.error.HTTPError('https://registry.invalid/blob', 307, 'redirect', {'Location': 'https://storage.invalid/blob?signature=private'}, None)
        with tempfile.TemporaryDirectory() as folder, patch.object(probe.urllib.request, 'build_opener') as opener, patch.object(probe.urllib.request, 'urlopen', return_value=io.BytesIO(content)) as external:
            opener.return_value.open.side_effect = redirect
            probe.download('https://registry.invalid/blob', Path(folder) / 'blob', digest, 'Basic private')
            # La petición al storage se crea solo desde la URL, sin headers ECR.
            self.assertEqual(external.call_args.args, ('https://storage.invalid/blob?signature=private',))

    def test_corrupt_registry_blob_is_rejected_without_completed_cache_file(self):
        expected = 'sha256:' + hashlib.sha256(b'expected').hexdigest()
        with tempfile.TemporaryDirectory() as folder, patch.object(probe.urllib.request, 'build_opener') as opener:
            path = Path(folder) / 'blob'
            opener.return_value.open.return_value = io.BytesIO(b'corrupt')
            with self.assertRaises(ValueError):
                probe.download('https://example.invalid/blob', path, expected, 'Basic private')
            self.assertFalse(path.exists())
            self.assertFalse(path.with_suffix('.part').exists())

    def test_cached_blob_is_rehashed_and_never_trusted_by_filename_alone(self):
        good = b'verified'
        digest = 'sha256:' + hashlib.sha256(good).hexdigest()
        with tempfile.TemporaryDirectory() as folder, patch.object(probe.urllib.request, 'build_opener') as opener:
            path = Path(folder) / 'blob'
            path.write_bytes(b'bad cache')
            opener.return_value.open.return_value = io.BytesIO(good)
            probe.download('https://example.invalid/blob', path, digest, 'Basic private')
            self.assertEqual(path.read_bytes(), good)
            opener.reset_mock()
            probe.download('https://example.invalid/blob', path, digest, 'Basic private')
            opener.assert_not_called()

    def test_oci_archive_keeps_original_manifest_digest_and_exact_reference(self):
        config = json.dumps({'os': 'linux', 'architecture': 'amd64'}).encode()
        layer = b'compressed layer'
        digest = lambda b: 'sha256:' + hashlib.sha256(b).hexdigest()
        manifest = {'schemaVersion': 2, 'mediaType': 'application/vnd.docker.distribution.manifest.v2+json',
                    'config': {'digest': digest(config), 'size': len(config)}, 'layers': [{'digest': digest(layer), 'size': len(layer)}]}
        raw = json.dumps(manifest).encode()
        blobs = {digest(raw): raw, digest(config): config, digest(layer): layer}
        reference = '123456789012.dkr.ecr.us-east-1.amazonaws.com/the-store/ui@' + digest(raw)
        def download(url, path, sha, auth):
            path.write_bytes(blobs[sha])
        with tempfile.TemporaryDirectory() as folder, patch.object(probe, 'download', side_effect=download):
            archive = Path(folder) / 'image.tar'
            probe.archive_image(reference, Path(folder) / 'cache', archive, 'Basic private')
            with tarfile.open(archive) as tar:
                index = json.load(tar.extractfile('index.json'))['manifests'][0]
                self.assertEqual(index['digest'], digest(raw))
                self.assertEqual(index['annotations']['io.containerd.image.name'], reference)
                self.assertEqual(tar.extractfile('blobs/sha256/' + digest(raw).split(':')[1]).read(), raw)

    def test_present_image_without_expected_repo_digest_cannot_pass(self):
        with patch.object(probe, 'call', return_value=json.dumps({'status': {'id': 'sha256:config', 'repoDigests': ['other@sha256:wrong']}})):
            with self.assertRaises(ValueError):
                probe.inspect('node', 'expected@sha256:manifest')


if __name__ == '__main__':
    unittest.main()
