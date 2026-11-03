#!/usr/bin/env python3
"""Carga explícita en ambos kind; check-external es de solo lectura para Terraform."""
import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import shlex
import sys

from acceso_kind import ROOT, private_write, require, validate_manifest
from ssm import run
from importlib.util import module_from_spec, spec_from_file_location
spec = spec_from_file_location('release', ROOT / 'scripts/seleccionar-release.py')
release = module_from_spec(spec)
spec.loader.exec_module(release)


def script(payload):
    code = base64.b64encode((ROOT / 'scripts/probes/imagenes_kind.py').read_bytes()).decode()
    config = base64.b64encode(json.dumps(payload).encode()).decode()
    return f'''set -eu
umask 077
folder=$(mktemp -d /tmp/the-store-images.XXXXXXXX)
trap 'rm -rf -- "$folder"' EXIT
printf %s {shlex.quote(code)} | base64 -d >"$folder/client.py"
printf %s {shlex.quote(config)} | base64 -d >"$folder/config.json"
env -i PATH=/usr/local/bin:/usr/bin:/bin AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null AWS_EC2_METADATA_DISABLED=false AWS_DEFAULT_REGION=us-east-1 python3 "$folder/client.py" "$folder/config.json"
'''


def execute(manifest_path, images, mode):
    validate_manifest(manifest_path)
    manifest = json.loads(Path(manifest_path).read_text())
    environment = json.loads((ROOT / 'config/entorno.json').read_text())
    folder = ROOT / '.local/t08/images'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    def probe(key):
        entry = manifest['clusters'][key]
        payload = {'images': images, 'mode': mode, 'region': environment['region'], 'cluster_name': entry['cluster_name'], 'cluster_uid': entry['cluster_uid']}
        output = run(environment['region'], entry['instance_id'], script(payload), folder / (mode + '-' + key + '.log'), timeout=2400 if mode == 'prepare' else 180)
        result = json.loads(output)
        require(result['status'] == 'PASS' and result['cluster_uid'] == entry['cluster_uid'] and result['role'] == 'LabRole' and len(result['nodes']) == 2 and all(set(v) == set(images) for v in result['nodes'].values()), 'Caché incompleta o identidad incorrecta')
        return key, result
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = dict(pool.map(probe, ('a', 'b')))
    validate_manifest(manifest_path)
    private_write(folder / (mode + '-report.json'), json.dumps(results, indent=2) + '\n')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'check', 'check-external'])
    parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    if args.mode == 'check-external':
        query = json.load(sys.stdin)
        execute(query['manifest'], json.loads(query['images']), 'check')
        print(json.dumps({'status': 'PASS'}))
    else:
        manifest = args.manifest or os.environ.get('THE_STORE_ACCESS_MANIFEST')
        require(manifest, 'Ejecutar dentro de acceso.py run')
        execute(manifest, release.select(args.version), args.mode)
        print('PASS: cinco imágenes por digest en los cuatro nodos kind; LabRole.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('FALLA caché kind: ' + type(exc).__name__ + '; revisar logs privados .local/t08/images', file=sys.stderr)
        sys.exit(1)
