#!/usr/bin/env python3
"""Prueba real: inventario ECR, rollback sin publicar, rechazo y UI HTTP local v1/v2."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pub', ROOT / 'scripts/publicar-imagenes.py')
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)



def terraform_selections(manifest, selected):
    directory = ROOT / '.local/t07'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    for index, version in enumerate(('v1', 'v2', 'v1')):
        plan = directory / f'select-{index}.tfplan'
        log = directory / f'select-{index}.log'
        with log.open('w') as output:
            log.chmod(0o600)
            pub.command(['terraform', f'-chdir={ROOT / "terraform/imagenes"}', 'plan', '-input=false', '-no-color',
                         '-var=release_manifest=' + str(pub.MANIFEST), '-var=app_version=' + version,
                         '-out=' + str(plan)], log=output, timeout=240)
        plan.chmod(0o600)
        data = json.loads(pub.command(['terraform', f'-chdir={ROOT / "terraform/imagenes"}', 'show', '-json', str(plan)]))
        assert all(item['change']['actions'] == ['no-op'] for item in data.get('resource_changes', []) if item['mode'] == 'managed'), 'La selección modifica recursos'
        assert data['planned_values']['outputs']['images']['value'] == selected[index], 'Terraform selecciona otros digests'
    with tempfile.TemporaryDirectory(prefix='t07-invalid-') as temp:
        for case in ('incomplete', 'wrong-digest'):
            invalid = copy.deepcopy(manifest)
            if case == 'incomplete':
                del invalid['versions']['v1']['carts']
            else:
                invalid['versions']['v1']['carts']['digest'] = 'sha256:' + '0' * 64
            path = Path(temp) / (case + '.json')
            pub.save(path, invalid)
            log = directory / ('reject-' + case + '.log')
            with log.open('w') as output:
                log.chmod(0o600)
                result = subprocess.run(['terraform', f'-chdir={ROOT / "terraform/imagenes"}', 'plan', '-input=false', '-no-color',
                                         '-var=release_manifest=' + str(path), '-var=app_version=v1'],
                                        stdout=output, stderr=subprocess.STDOUT, timeout=240)
            assert result.returncode == 1 and 'Publicación incompleta' in log.read_text(), 'Terraform aceptó manifest inválido o falló por otra causa'
    print('Terraform: v1/v2/v1 sin cambios de recursos; manifests inválidos rechazados', flush=True)


def main():
    manifest = json.loads(pub.MANIFEST.read_text())
    repos = pub.repositories()
    selected = [pub.validate(manifest, version, repos) for version in ('v1', 'v2', 'v1')]
    assert selected[0] == selected[2], 'Rollback cambió referencias'
    for index, version in enumerate(('v1', 'v2')):
        pub.save(ROOT / f'.local/t07/references-{version}.json', {'app_version': version, 'images': selected[index]})
    assert all(selected[0][s] != selected[1][s] for s in pub.SERVICES), 'Versiones con el mismo digest'
    print('ECR: 10 imágenes; selección v1/v2/v1 estable', flush=True)
    partial = copy.deepcopy(manifest)
    del partial['versions']['v1']['checkout']
    try:
        pub.validate(partial, 'v1', repos)
    except ValueError as exc:
        assert 'incompleta' in str(exc)
    else:
        raise AssertionError('Selección parcial aceptada')
    corrupt = copy.deepcopy(manifest)
    corrupt['versions']['v1']['carts']['digest'] = 'sha256:' + '0' * 64
    try:
        pub.validate(corrupt, 'v1', repos)
    except ValueError as exc:
        assert 'Digest incorrecto' in str(exc)
    else:
        raise AssertionError('Digest incorrecto aceptado')
    try:
        pub.publish(pub.MANIFEST, 'v1')
    except ValueError as exc:
        assert 'ya publicada' in str(exc)
    else:
        raise AssertionError('Publicador aceptó reescritura')
    terraform_selections(manifest, selected)
    # Deliberately attempt an immutable tag overwrite with the *different* v2 manifest.
    repo = 'the-store/ui'
    settings = pub.aws('ecr', 'describe-repositories', '--repository-names', repo)['repositories'][0]
    assert settings['imageTagMutability'] == 'IMMUTABLE', 'No intentar reescritura sin inmutabilidad'
    image = pub.aws('ecr', 'batch-get-image', '--repository-name', repo, '--image-ids', 'imageTag=v2')['images'][0]
    p = subprocess.run(['aws', '--region', pub.REGION, 'ecr', 'put-image', '--repository-name', repo,
                        '--image-tag', 'v1', '--image-manifest', image['imageManifest']], text=True, capture_output=True, timeout=90)
    assert p.returncode != 0 and '(ImageTagAlreadyExistsException)' in p.stderr, 'ECR no rechazó reescritura esperada'
    print('Reescritura rechazada por publicador y ECR', flush=True)
    evidence = {'selection_v1_v2_v1': 'passed', 'terraform_selection': '3 plans with no resource changes; incomplete/wrong digest rejected', 'immutable_rewrite': 'ImageTagAlreadyExistsException', 'invalid_selections': 'incomplete and incorrect digest rejected', 'ui_http': {}}
    for version in ('v1', 'v2'):
        name = 't07-ui-' + uuid.uuid4().hex[:12]
        # Uses the already published local image. No build/push and no personal credentials.
        pub.command(['docker', 'run', '--pull=never', '--detach', '--rm', '--name', name, '--publish', '127.0.0.1::8080', repos['ui'] + ':' + version])
        try:
            ports = json.loads(pub.command(['docker', 'inspect', name]))[0]['NetworkSettings']['Ports']['8080/tcp']
            url = 'http://127.0.0.1:' + ports[0]['HostPort'] + '/catalog'
            deadline = time.monotonic() + 120
            while True:
                try:
                    with urllib.request.urlopen(url, timeout=5) as response:
                        html = response.read().decode()
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError('UI no responde: ' + version)
                    time.sleep(1)
            match = re.search(r'<span\s+id="store-version"[^>]*>([^<]+)</span>', html)
            assert match and match[1] == 'The Store · ' + version, 'UI no muestra versión correcta'
            evidence['ui_http'][version] = dict(status=200, visible_text=match[1])
            print('UI HTTP 200: ' + match[1], flush=True)
        finally:
            pub.command(['docker', 'stop', '--time', '10', name], timeout=30)
    # Validate rollback once more after the attempted overwrite.
    assert pub.validate(manifest, 'v1', repos) == selected[0]
    path = ROOT / '.local/t07/publication-evidence.json'
    pub.save(path, evidence)
    path.chmod(0o600)


if __name__ == '__main__':
    main()
