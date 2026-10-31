#!/usr/bin/env python3
"""Ejecuta un comando con ambos túneles SSM y limpia al terminar (incluye interrupciones)."""
import argparse
import os
import shutil
import signal
import subprocess
import sys

from acceso_kind import AccessSession, validate_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run'])
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Falta comando: acceso.py run -- COMANDO ...')
    for tool in ('aws', 'terraform', 'kubectl', 'session-manager-plugin'):
        if not shutil.which(tool):
            parser.error('Falta herramienta: ' + tool)
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    child = None
    try:
        with AccessSession() as access:
            env = {key: value for key, value in os.environ.items() if not key.startswith('KUBE_') and key not in ('KUBECONFIG', 'KUBERNETES_SERVICE_HOST', 'KUBERNETES_SERVICE_PORT')}
            env.update(TF_VAR_access_manifest=str(access.manifest_path), THE_STORE_ACCESS_MANIFEST=str(access.manifest_path))
            print('Acceso verificado a kind a/b; TLS y destinos distintos.', flush=True)
            child = subprocess.Popen(command, env=env, start_new_session=True)
            try:
                code = child.wait()
                if code:
                    # client-go no reenvía stderr del plugin en todos los errores.
                    # Mostrar el motivo claro si el comando perdió acceso.
                    validate_manifest(access.manifest_path)
                return code
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGINT)
                    try:
                        child.wait(timeout=30)
                    except subprocess.TimeoutExpired:
                        os.killpg(child.pid, signal.SIGKILL); child.wait()
    except KeyboardInterrupt:
        print('Interrumpido; acceso retirado.', file=sys.stderr)
        return 130
    except Exception as exc:
        print('FALLA acceso:', str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
