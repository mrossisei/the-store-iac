#!/usr/bin/env python3
"""Pull por digest en ambos hosts vía SSM, sólo con credenciales IMDS de LabRole."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ssm import run
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publicador', ROOT / 'scripts/publicar-imagenes.py')
publicador = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publicador)

# All AWS/Docker calls capture output. No password/config is returned in SSM logs.
HOST = r'''
import base64, json, os, subprocess, tempfile
payload = json.loads(base64.b64decode('PAYLOAD'))
def call(args, stdin=None):
    p = subprocess.run(args, input=stdin, text=True, capture_output=True, timeout=600)
    if p.returncode:
        raise RuntimeError(args[0] + ' ' + args[1] + ' failed: exit ' + str(p.returncode))
    return p.stdout
with tempfile.TemporaryDirectory(prefix='t07-pull-') as directory:
    os.environ.update(HOME=directory, DOCKER_CONFIG=directory, AWS_CONFIG_FILE='/dev/null',
                      AWS_SHARED_CREDENTIALS_FILE='/dev/null', AWS_EC2_METADATA_DISABLED='false',
                      AWS_DEFAULT_REGION=payload['region'], AWS_PAGER='')
    identity = json.loads(call(['aws', 'sts', 'get-caller-identity', '--output', 'json']))
    assert ':assumed-role/LabRole/' in identity['Arn'], 'Expected instance LabRole'
    registry = next(iter(payload['versions']['v1'].values())).split('/')[0]
    assert identity['Account'] == registry.split('.')[0], 'Wrong account'
    password = call(['aws', 'ecr', 'get-login-password', '--region', payload['region']])
    call(['docker', 'login', '--username', 'AWS', '--password-stdin', registry], password)
    del password
    checks = []
    for version, services in payload['versions'].items():
        for service, reference in services.items():
            call(['docker', 'pull', '--platform', 'linux/amd64', reference])
            image = json.loads(call(['docker', 'image', 'inspect', reference]))[0]
            assert image['Os'] == 'linux' and image['Architecture'] == 'amd64', 'Wrong platform'
            assert reference in image['RepoDigests'], 'Digest mismatch'
            checks.append(dict(version=version, service=service, reference=reference, platform='linux/amd64'))
    print(json.dumps(dict(identity=identity['Arn'], pulls=checks)))
'''


def host_script(versions):
    payload = base64.b64encode(json.dumps({'region': publicador.REGION, 'versions': versions}).encode()).decode()
    # A clean environment prevents env vars, CLI profiles or credentials files from shadowing IMDS.
    return "set -eu\numask 077\nenv -i PATH=/usr/local/bin:/usr/bin:/bin python3 <<'T07PY'\n" + HOST.replace('PAYLOAD', payload) + '\nT07PY\n'


def instance_ids(coord):
    if coord.get('schema') != 1 or coord.get('region') != publicador.REGION or coord.get('status') not in ('ready', 'hosts_ready', 'compute_ready'):
        raise ValueError('Coordinación todavía no lista')
    compute = coord['compute']
    raw = compute.get('instance_ids', compute)
    ids = {zone: value.get('instance_id') if isinstance(value, dict) else value for zone, value in raw.items()}
    if set(ids) != {'a', 'b'} or not all(isinstance(value, str) and re.fullmatch('i-[a-f0-9]{8,17}', value) for value in ids.values()) or ids['a'] == ids['b']:
        raise ValueError('Se requieren IDs distintos a/b')
    return ids


def ensure_current(path, expected):
    current = json.loads(path.read_text())
    ids = instance_ids(current)
    if current.get('generation', 0) != expected.get('generation', 0) or ids != instance_ids(expected):
        raise ValueError('Cambió la generación o los hosts; releer coordinación antes de operar')
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--coordination', type=Path, required=True)
    parser.add_argument('--generation', type=int, help='Exigir la generación acordada con el padre')
    parser.add_argument('--manifest', type=Path, default=publicador.MANIFEST)
    parser.add_argument('--evidence', type=Path, default=ROOT / '.local/t07/pull-evidence.json')
    args = parser.parse_args()
    coordination = json.loads(args.coordination.read_text())
    ids = instance_ids(coordination)
    if args.generation is not None and coordination.get('generation') != args.generation:
        parser.error('La generación no coincide con la acordada')
    manifest = json.loads(args.manifest.read_text())
    repos = publicador.repositories()
    versions = {v: publicador.validate(manifest, v, repos) for v in ('v1', 'v2')}
    results = {}
    publicador.save(args.evidence, results)
    args.evidence.chmod(0o600)
    def probe(zone, instance):
        ensure_current(args.coordination, coordination)
        output = run(publicador.REGION, instance, host_script(versions), args.evidence.parent / ('pull-' + zone + '.log'), timeout=1800)
        ensure_current(args.coordination, coordination)
        result = json.loads(output.strip())
        expected = {(v, s, ref, 'linux/amd64') for v, services in versions.items() for s, ref in services.items()}
        actual = {(item['version'], item['service'], item['reference'], item['platform']) for item in result['pulls']}
        if len(result['pulls']) != 10 or actual != expected or ':assumed-role/LabRole/' not in result['identity']:
            raise ValueError('Resultado incompleto en ' + zone)
        return zone, dict(instance_id=instance, generation=coordination.get('generation', 0), **result)
    errors = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(probe, zone, instance) for zone, instance in ids.items()]
        for future in as_completed(futures):
            try:
                zone, result = future.result()
            except Exception as exc:
                errors.append(str(exc))
                continue
            results[zone] = result
            publicador.save(args.evidence, results)
            args.evidence.chmod(0o600)
            print(zone + ': 10 pulls linux/amd64 con LabRole comprobados', flush=True)
    if errors:
        raise RuntimeError('; '.join(errors))


if __name__ == '__main__':
    main()
