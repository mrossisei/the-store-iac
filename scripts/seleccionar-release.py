#!/usr/bin/env python3
"""Adaptador external: valida una release existente en ECR, sin compilar/publicar."""
import importlib.util
import json
from pathlib import Path
import sys
spec = importlib.util.spec_from_file_location('publisher', Path(__file__).with_name('publicar-imagenes.py'))
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)
APP_MANIFEST = publisher.ROOT / 'terraform/imagenes/releases-aplicacion.json'


def select(version, manifest_path=APP_MANIFEST):
    if version not in ('v1', 'v2'):
        raise ValueError('Versión inválida')
    account = publisher.aws('sts', 'get-caller-identity')['Account']
    repos = {s: f'{account}.dkr.ecr.{publisher.REGION}.amazonaws.com/{publisher.CONFIG["project"]}/{s}' for s in publisher.SERVICES}
    return publisher.validate(json.loads(Path(manifest_path).read_text()), version, repos)


if __name__ == '__main__':
    try:
        query = json.load(sys.stdin)
        version = query['app_version']
        print(json.dumps({'app_version': version, 'images': json.dumps(select(version, query.get('manifest', APP_MANIFEST)), sort_keys=True)}))
    except Exception as exc:
        print('No se pudo validar release ECR: ' + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
