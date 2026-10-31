#!/usr/bin/env python3
"""Sonda temporal T03/T10: APIs kind por SSM/TLS y controles de fallo del arnés."""
import argparse
import json
import os
from pathlib import Path
import re
import signal
import socket
import subprocess
import tempfile
import time

from ssm import run, aws

ROOT = Path(__file__).resolve().parents[1]


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    local = ROOT / '.local'
    local.mkdir(exist_ok=True, mode=0o700)
    config = json.loads((ROOT / 'config/entorno.json').read_text())
    compute = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json', 'compute'], timeout=90))
    processes, handles, session_logs = [], [], []
    with tempfile.TemporaryDirectory(prefix='t03-apis-', dir=local) as temporary:
        folder = Path(temporary)
        try:
            specs = {}
            for key in ('a', 'b'):
                port = config['zones'][key]['local_api_port']
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', port))  # No reemplazar túneles del operador.
                kubeconfig = run(config['region'], compute[key]['instance_id'], 'cat /var/lib/the-store/kubeconfig', folder / (key + '-read.log'), timeout=90)
                original = 'server: https://127.0.0.1:' + str(config['kind']['api_port'])
                assert kubeconfig.count(original) == 1, 'Endpoint kubeconfig inesperado'
                path = folder / (key + '.kubeconfig')
                path.write_text(kubeconfig.replace(original, 'server: https://127.0.0.1:' + str(port)))
                path.chmod(0o600)
                log = local / ('t03-api-' + key + '.log')
                handle = log.open('w'); log.chmod(0o600); handles.append(handle); session_logs.append(log)
                process = subprocess.Popen(['aws', '--region', config['region'], '--no-cli-pager', 'ssm', 'start-session', '--target', compute[key]['instance_id'],
                                            '--document-name', 'AWS-StartPortForwardingSession', '--parameters', json.dumps({'portNumber': [str(config['kind']['api_port'])], 'localPortNumber': [str(port)]})],
                                           stdout=handle, stderr=handle, start_new_session=True)
                processes.append(process)
                context = 'kind-' + config['zones'][key]['cluster_name']
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('El túnel SSM terminó; revisar log local ' + key)
                    result = subprocess.run(['kubectl', '--kubeconfig', str(path), '--context', context, '--request-timeout=5s', 'get', '--raw', '/readyz'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0 and result.stdout.strip() == 'ok':
                        break
                    time.sleep(2)
                else:
                    raise RuntimeError('API ' + key + ' no accesible por TLS/SSM')
                specs[key] = {'kubeconfig': str(path), 'context': context}
            def verify(specs, name):
                cfg = folder / (name + '.json'); cfg.write_text(json.dumps({'clusters': specs}))
                report = local / ('t03-api-' + name + '.json')
                result = subprocess.run([str(ROOT / 'verificar.sh'), '--config', str(cfg), '--mode', 'bootstrap', '--report', str(report)], capture_output=True, text=True, timeout=240)
                log = local / ('t03-api-' + name + '-checks.log'); log.write_text(result.stdout + '\n' + result.stderr); log.chmod(0o600)
                return result.returncode, json.loads(report.read_text())
            code, report = verify(specs, 'correctas')
            assert code == 0 and report['status'] == 'PASS', 'Falló T10 sobre APIs privadas reales'
            print('PASS: T10 sobre ambos kind mediante SSM, CA y certificado validados', flush=True)
            code, report = verify({'a': specs['a'], 'b': specs['a']}, 'duplicadas')
            assert code == 1 and any(r['check'] == 'identidades-distintas' and r['status'] == 'FAIL' for r in report['results'])
            print('PASS: T10 rechaza dos contextos que apuntan al mismo kind', flush=True)
            # Puerto reservado sin listen: conexión rechazada, contexto/certificado válidos.
            with socket.socket() as closed:
                closed.bind(('127.0.0.1', 0))
                unavailable = folder / 'b-unavailable.kubeconfig'
                unavailable.write_text(Path(specs['b']['kubeconfig']).read_text().replace(
                    'server: https://127.0.0.1:' + str(config['zones']['b']['local_api_port']),
                    'server: https://127.0.0.1:' + str(closed.getsockname()[1])))
                unavailable.chmod(0o600)
                code, report = verify({'a': specs['a'], 'b': dict(specs['b'], kubeconfig=str(unavailable))}, 'inaccesible')
                assert code == 1 and any(r['check'] == 'b:bootstrap' and r['status'] == 'FAIL' for r in report['results'])
            print('PASS: T10 rechaza una API inaccesible con contexto válido', flush=True)
        finally:
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL); process.wait()
            for handle in handles:
                handle.close()
            for log in session_logs:
                match = re.search(r'SessionId:\s*(\S+)', log.read_text())
                if match:
                    active = aws(config['region'], 'ssm', 'describe-sessions', '--state', 'Active', '--filters', json.dumps([{'key': 'SessionId', 'value': match.group(1)}]))['Sessions']
                    if any(s['SessionId'] == match.group(1) for s in active):
                        aws(config['region'], 'ssm', 'terminate-session', '--session-id', match.group(1))


if __name__ == '__main__':
    main()
