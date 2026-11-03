#!/usr/bin/env python3
"""Cliente EC2: descarga blobs OCI autenticado con LabRole e importa ambos nodos."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request


def call(args, timeout=180):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(args[0] + ' falló: ' + str(result.returncode))
    return result.stdout


def checked_digest(digest):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
        raise ValueError('Digest inválido')
    return digest.split(':', 1)[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def file_sha256(stream):
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    return digest.hexdigest()


def download(url, destination, digest, auth):
    expected = checked_digest(digest)
    if destination.exists():
        with destination.open('rb') as stream:
            if file_sha256(stream) == expected:
                return
        destination.unlink()
    request = urllib.request.Request(url, headers={'Authorization': auth, 'Accept': 'application/vnd.docker.distribution.manifest.v2+json, application/vnd.oci.image.manifest.v1+json'})
    try:
        response = urllib.request.build_opener(NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise RuntimeError('Registry rechazó descarga: ' + str(exc.code)) from None
        target = exc.headers['Location']
        exc.close()
        if not target.startswith('https://'):
            raise ValueError('Redirección insegura')
        # No reenviar el password ECR al host de almacenamiento del blob.
        response = urllib.request.urlopen(target, timeout=60)
    temporary = destination.with_suffix('.part')
    try:
        checksum = hashlib.sha256()
        with response, temporary.open('wb') as stream:
            while chunk := response.read(1024 * 1024):
                checksum.update(chunk)
                stream.write(chunk)
        if checksum.hexdigest() != expected:
            raise ValueError('Blob no coincide con digest')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def archive_image(reference, cache, archive, auth):
    repo, digest = reference.split('@')
    registry, name = repo.split('/', 1)
    root = 'https://' + registry + '/v2/' + name
    blobdir = cache / 'blobs/sha256'
    blobdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest_path = blobdir / checked_digest(digest)
    download(root + '/manifests/' + digest, manifest_path, digest, auth)
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get('schemaVersion') != 2 or 'config' not in manifest or 'layers' not in manifest:
        raise ValueError('Se requiere manifest de plataforma única')
    descriptors = [manifest['config']] + manifest['layers']
    for blob in descriptors:
        download(root + '/blobs/' + blob['digest'], blobdir / checked_digest(blob['digest']), blob['digest'], auth)
    config = json.loads((blobdir / checked_digest(manifest['config']['digest'])).read_bytes())
    if config['architecture'] != 'amd64' or config['os'] != 'linux':
        raise ValueError('Plataforma distinta de linux/amd64')
    descriptor = {'mediaType': manifest['mediaType'], 'digest': digest, 'size': manifest_path.stat().st_size,
                  'platform': {'architecture': 'amd64', 'os': 'linux'},
                  'annotations': {'io.containerd.image.name': reference, 'org.opencontainers.image.ref.name': reference}}
    index = cache / 'index.json'
    index.write_text(json.dumps({'schemaVersion': 2, 'manifests': [descriptor]}))
    layout = cache / 'oci-layout'
    layout.write_text('{"imageLayoutVersion":"1.0.0"}')
    with tarfile.open(archive, 'w') as tar:
        tar.add(index, arcname='index.json')
        tar.add(layout, arcname='oci-layout')
        for item in {digest, *(d['digest'] for d in descriptors)}:
            tar.add(blobdir / checked_digest(item), arcname='blobs/sha256/' + checked_digest(item))


def inspect(node, reference):
    value = json.loads(call(['docker', 'exec', node, 'crictl', 'inspecti', reference]))['status']
    if reference not in value.get('repoDigests', []):
        raise ValueError('CRI no conserva el digest exacto')
    return {'reference': reference, 'id': value['id']}


def main(payload):
    cluster = payload['cluster_name']
    nodes = [cluster + '-control-plane', cluster + '-worker']
    actual = call(['kind', 'get', 'nodes', '--name', cluster]).split()
    if set(actual) != set(nodes):
        raise ValueError('Nodos kind inesperados')
    os.environ['KUBECONFIG'] = '/var/lib/the-store/kubeconfig'
    uid = json.loads(call(['kubectl', 'get', 'namespace', 'kube-system', '-o', 'json']))['metadata']['uid']
    if uid != payload['cluster_uid']:
        raise ValueError('Cambió identidad kind')
    identity = json.loads(call(['aws', '--region', payload['region'], 'sts', 'get-caller-identity', '--output', 'json']))
    if ':assumed-role/LabRole/' not in identity['Arn']:
        raise ValueError('Se requiere perfil de instancia LabRole')
    images = payload['images']
    if len(images) != 5 or any(not ref.startswith(identity['Account'] + '.dkr.ecr.' + payload['region'] + '.amazonaws.com/the-store/') for ref in images.values()):
        raise ValueError('Registry no coincide con cuenta/región')
    with tempfile.TemporaryDirectory(prefix='t08-images-') as temp:
        folder = Path(temp)
        if payload['mode'] == 'prepare':
            password = call(['aws', '--region', payload['region'], 'ecr', 'get-login-password']).strip()
            auth = 'Basic ' + base64.b64encode(('AWS:' + password).encode()).decode()
            del password
            cache = Path('/var/cache/the-store/images')
            cache.mkdir(parents=True, exist_ok=True, mode=0o700)
            for service, reference in images.items():
                archive = folder / (service + '.tar')
                archive_image(reference, cache, archive, auth)
                call(['kind', 'load', 'image-archive', '--name', cluster, str(archive)], timeout=600)
                archive.unlink()
            del auth
        checks = {node: {service: inspect(node, ref) for service, ref in images.items()} for node in nodes}
    print(json.dumps({'status': 'PASS', 'cluster_uid': uid, 'role': 'LabRole', 'nodes': checks}))


if __name__ == '__main__':
    try:
        with open('/var/lock/the-store-images.lock', 'a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            main(json.loads(Path(sys.argv[1]).read_text()))
    except Exception as exc:
        # urllib/process exceptions pueden incluir URLs firmadas/passwords.
        print('FALLA imágenes kind: ' + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
