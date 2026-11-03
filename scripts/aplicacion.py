#!/usr/bin/env python3
"""Operación T08: acceso a ambos kind, precarga y plan revisado en una misma sesión."""
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

from acceso_kind import AccessSession, ROOT, private_write, require


def app_version():
    text = (ROOT / 'terraform/aplicacion/terraform.tfvars').read_text()
    versions = re.findall(r'^\s*app_version\s*=\s*"(v1|v2)"\s*(?:#.*)?$', text, flags=re.M)
    require(len(versions) == 1, 'Definir exactamente app_version v1/v2 en terraform/aplicacion/terraform.tfvars')
    return versions[0]


def review(value, destroying=False):
    changes = [r for r in value.get('resource_changes', []) if r['mode'] == 'managed' and r['change']['actions'] != ['no-op']]
    allowed = ('module.app_a[0].', 'module.app_b[0].', 'module.politicas_a[0].', 'module.politicas_b[0].')
    resource_types = {'kubernetes_namespace_v1', 'kubernetes_secret_v1', 'kubernetes_deployment_v1', 'kubernetes_service_v1', 'kubernetes_network_policy_v1'}
    require(all(r['address'].startswith(allowed) and r['type'] in resource_types for r in changes), 'Plan incluye recursos fuera de la aplicación/políticas kind')
    require(all(r['change']['actions'] == ['delete'] for r in changes) if destroying else all('delete' not in r['change']['actions'] or r['type'] == 'kubernetes_network_policy_v1' for r in changes), 'Plan propone eliminación/reemplazo inesperado; revisar manualmente')
    return dict(Counter('/'.join(r['change']['actions']) for r in changes))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'plan', 'apply', 'destroy'])
    args = parser.parse_args()
    folder = ROOT / '.local/t08/operation'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    with AccessSession() as access:
        env = dict(os.environ, TF_VAR_access_manifest=str(access.manifest_path), THE_STORE_ACCESS_MANIFEST=str(access.manifest_path), TF_IN_AUTOMATION='1')
        def tf(label, *command):
            result = subprocess.run(['terraform', '-chdir=' + str(ROOT / 'terraform/aplicacion'), *command], env=env, capture_output=True, text=True, timeout=1200)
            private_write(folder / (label + '.log'), result.stdout + result.stderr)
            require(result.returncode == 0, 'Terraform ' + label + ' falló; revisar log privado')
            return result.stdout
        if args.action != 'destroy':
            spec = importlib.util.spec_from_file_location('cache', ROOT / 'scripts/preparar-imagenes.py')
            cache = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cache)
            cache.execute(access.manifest_path, cache.release.select(app_version()), 'prepare')
            print('PASS: imágenes registradas por digest en los cuatro nodos con LabRole.', flush=True)
        if args.action == 'prepare':
            return
        plan = folder / (args.action + '.tfplan')
        tf('plan', 'plan', '-input=false', '-no-color', '-out=' + str(plan), *(['-destroy'] if args.action == 'destroy' else []))
        plan.chmod(0o600)
        counts = review(json.loads(tf('plan-json', 'show', '-json', str(plan))), args.action == 'destroy')
        print('Plan revisado, solo objetos propios de ambos kind: ' + json.dumps(counts), flush=True)
        if args.action != 'plan':
            tf('apply', 'apply', '-input=false', '-no-color', str(plan))
            print('PASS: operación aplicada a ambos kind.', flush=True)
        # La sesión cierra y su plan guardado queda deliberadamente inutilizable.


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:
        import traceback
        folder = ROOT / '.local/t08/operation'
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        private_write(folder / 'error.log', traceback.format_exc())
        print('FALLA aplicación: ' + type(exc).__name__ + '; revisar .local/t08/operation y acceso.', file=sys.stderr)
        sys.exit(1)
