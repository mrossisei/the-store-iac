#!/usr/bin/env python3
"""ExecCredential privado para client-go. No ejecutar manualmente ni registrar stdout."""
import base64
import json
from pathlib import Path
import sys

from acceso_kind import invoke, validate_manifest


def main():
    try:
        path, key = sys.argv[1:]
        if key not in ('a', 'b'):
            raise ValueError('Destino incorrecto')
        validate_manifest(path)
        entry = json.loads(Path(path).read_text())['clusters'][key]
        config = json.loads(invoke(['kubectl', '--kubeconfig', entry['kubeconfig'], 'config', 'view', '--raw', '-o', 'json']))
        user = config['users'][0]['user']
        # Solo client-go recibe este JSON por un pipe; nunca Terraform state.
        print(json.dumps({'apiVersion': 'client.authentication.k8s.io/v1', 'kind': 'ExecCredential', 'status': {
            'clientCertificateData': base64.b64decode(user['client-certificate-data']).decode(),
            'clientKeyData': base64.b64decode(user['client-key-data']).decode(),
        }}))
        return 0
    except Exception:
        print('Acceso kind inválido: comprobar ambos túneles, identidades y TLS con scripts/acceso.py run.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
