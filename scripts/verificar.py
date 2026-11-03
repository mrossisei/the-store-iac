#!/usr/bin/env python3
"""T10: verifica ambos kind; produce evidencia JSON y falla ante sondas inválidas."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]


class CheckError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise CheckError(message)


def command(args, timeout=45, input=None, allowed=(0,), log=None):
    try:
        result = subprocess.run(args, input=input, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CheckError(type(exc).__name__) from exc
    if log is not None:
        Path(log).write_text(result.stdout + '\n' + result.stderr)
        Path(log).chmod(0o600)
    require(result.returncode in allowed, f'{args[0]} terminó con código {result.returncode}')
    return result


def curl_result(result, blocked=False):
    # Un timeout de kubectl/exec no es un timeout comprobado de curl.
    if blocked:
        require(result.returncode == 28 and result.stdout.strip() == '000',
                f'No se probó bloqueo TCP: curl={result.returncode}, HTTP={result.stdout.strip()}')
    else:
        require(result.returncode == 0 and re.fullmatch(r'[1-5][0-9]{2}', result.stdout.strip()),
                f'No se probó conexión HTTP: curl={result.returncode}, HTTP={result.stdout.strip()}')


def ready(items, count):
    active = [p for p in items if not p['metadata'].get('deletionTimestamp')]
    return len(active) == count and all(p['status'].get('phase') == 'Running' and
        any(c['type'] == 'Ready' and c['status'] == 'True' for c in p['status'].get('conditions', [])) for p in active)


def compare_snapshots(before, after, expectation):
    require(set(before) == set(after), 'Cambió el conjunto de clústeres')
    for key in before:
        require(before[key]['cluster_uid'] == after[key]['cluster_uid'], 'Cambió la identidad del clúster')
        if expectation == 'unchanged':
            require(before[key]['pods'] == after[key]['pods'], 'Cambió UID/restarts/imagen de algún pod')
        elif expectation == 'rollback':
            require(before[key]['images'] == after[key]['images'], 'Rollback no recuperó las imágenes originales')
            require(before[key]['runtime_images'] == after[key]['runtime_images'], 'Rollback no recuperó los digests reales')
        elif expectation == 'rollout':
            require(before[key]['images'] != after[key]['images'], 'El rollout no cambió las imágenes')
            require(before[key]['pods'] != after[key]['pods'], 'El rollout no renovó pods')


class Cluster:
    def __init__(self, spec, namespace):
        self.spec, self.namespace = spec, namespace
        self.base = ['kubectl', '--kubeconfig', spec['kubeconfig'], '--context', spec['context'], '--request-timeout=20s']
        self.created = []

    def run(self, *args, **kwargs):
        return command(self.base + list(args), **kwargs)

    def get(self, *args):
        return json.loads(self.run('get', *args, '-o', 'json').stdout)

    def execute(self, pod, *args, **kwargs):
        return self.run('exec', '-n', self.namespace, pod, '--', *args, **kwargs)

    def snapshot(self):
        pods = self.get('pods', '-n', self.namespace)['items']
        deployments = self.get('deployments', '-n', self.namespace)['items']
        services = {d['metadata']['name'] for d in deployments}
        pods = [p for p in pods if p['metadata'].get('labels', {}).get('app') in services]
        return {
            'cluster_uid': self.get('namespace', 'kube-system')['metadata']['uid'],
            'pods': {p['metadata']['name']: {
                'uid': p['metadata']['uid'],
                'containers': [{k: c.get(k) for k in ('name', 'imageID', 'restartCount')} for c in p['status'].get('containerStatuses', [])]
            } for p in pods if not p['metadata'].get('deletionTimestamp')},
            'runtime_images': {service: sorted({c.get('imageID', '') for p in pods if p['metadata'].get('labels', {}).get('app') == service for c in p['status'].get('containerStatuses', [])}) for service in {d['metadata']['name'] for d in deployments}},
            'images': {d['metadata']['name']: [c['image'] for c in d['spec']['template']['spec']['containers']] for d in deployments},
        }

    def bootstrap(self):
        nodes = self.get('nodes')['items']
        require(len(nodes) == 2 and all(any(c['type'] == 'Ready' and c['status'] == 'True' for c in n['status']['conditions']) for n in nodes), 'Se requieren dos nodos Ready')
        self.run('rollout', 'status', '-n', 'kube-system', 'daemonset/calico-node', '--timeout=90s', timeout=100)
        require(not self.get('pods', '-n', 'kube-system', '-l', 'k8s-app=kindnet')['items'], 'kindnet debe estar deshabilitado')
        return self.get('namespace', 'kube-system')['metadata']['uid']

    def application(self, expected):
        for service, count in expected.items():
            self.run('rollout', 'status', '-n', self.namespace, 'deployment/' + service, '--timeout=120s', timeout=130)
            deployment = self.get('deployment', service, '-n', self.namespace)
            require(deployment['spec']['replicas'] == count, f'{service}: réplicas deseadas incorrectas')
            require(ready(self.get('pods', '-n', self.namespace, '-l', 'app=' + service)['items'], count), f'{service}: pods no Ready o conteo incorrecto')

    def pod(self, service):
        pods = self.get('pods', '-n', self.namespace, '-l', 'app=' + service)['items']
        candidates = [p for p in pods if ready([p], 1)]
        require(bool(candidates), 'Sin pod Ready para ' + service)
        return candidates[0]['metadata']['name']

    def http_probe(self, source, destination, blocked=False):
        pod = self.pod(source)
        self.execute(pod, 'curl', '--version')
        # Conocer IP y puerto antes de una sonda negativa evita aceptar error DNS.
        service = self.get('service', destination, '-n', self.namespace)
        ip, port = service['spec']['clusterIP'], service['spec']['ports'][0]['port']
        require(ip not in ('None', ''), 'El destino no tiene ClusterIP')
        self.execute(pod, 'curl', '-sS', '--max-time', '3', '-o', '/dev/null', '-w', '%{http_code}', 'http://127.0.0.1:8080/')
        result = self.execute(pod, 'curl', '-sS', '--max-time', '4', '-o', '/dev/null', '-w', '%{http_code}', f'http://{ip}:{port}/', allowed=tuple(range(256)))
        curl_result(result, blocked)

    def credentials(self, service):
        pod = self.pod(service)
        data = self.get('pod', pod, '-n', self.namespace)
        for container in data['spec']['containers']:
            require(not any(e['name'] in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN') for e in container.get('env', [])), 'Credenciales estáticas en PodSpec')
        self.execute(pod, 'sh', '-c', '[ -z "${AWS_ACCESS_KEY_ID:-}${AWS_SECRET_ACCESS_KEY:-}${AWS_SESSION_TOKEN:-}" ]')
        token = self.execute(pod, 'curl', '--noproxy', '*', '-fsS', '--max-time', '5', '-X', 'PUT', '-H',
                             'X-aws-ec2-metadata-token-ttl-seconds: 30', 'http://169.254.169.254/latest/api/token').stdout.strip()
        role = self.execute(pod, 'curl', '--noproxy', '*', '-fsS', '--max-time', '5', '-H',
                            'X-aws-ec2-metadata-token: ' + token, 'http://169.254.169.254/latest/meta-data/iam/security-credentials/').stdout.strip()
        require(role == 'LabRole', 'El pod no obtiene LabRole por IMDSv2')
        temporary = json.loads(self.execute(pod, 'curl', '--noproxy', '*', '-fsS', '--max-time', '5', '-H',
                                           'X-aws-ec2-metadata-token: ' + token,
                                           'http://169.254.169.254/latest/meta-data/iam/security-credentials/' + role).stdout)
        require(temporary.get('Code') == 'Success' and temporary.get('AccessKeyId', '').startswith('ASIA'), 'No se recibieron credenciales temporales')
        require(datetime.fromisoformat(temporary['Expiration'].replace('Z', '+00:00')) > datetime.now(timezone.utc), 'Credenciales expiradas')

    def stranger(self):
        name = 'verify-' + uuid.uuid4().hex[:10]
        body = {'apiVersion': 'v1', 'kind': 'Pod', 'metadata': {'name': name, 'namespace': self.namespace, 'labels': {'probe': name}},
                'spec': {'restartPolicy': 'Never', 'automountServiceAccountToken': False,
                         'containers': [{'name': 'probe', 'image': 'curlimages/curl:8.12.1', 'command': ['sleep', '300']}]}}
        self.created.append(name)
        self.run('create', '-f', '-', input=json.dumps(body))
        self.run('wait', '-n', self.namespace, '--for=condition=Ready', 'pod/' + name, '--timeout=120s', timeout=130)
        self.execute(name, 'curl', '--version')
        for destination in ('ui', 'catalog'):
            service = self.get('service', destination, '-n', self.namespace)
            ip, port = service['spec']['clusterIP'], service['spec']['ports'][0]['port']
            curl_result(self.execute(name, 'curl', '-sS', '--max-time', '4', '-o', '/dev/null', '-w', '%{http_code}', f'http://{ip}:{port}/', allowed=tuple(range(256))), True)

    def cleanup(self):
        for name in self.created:
            self.run('delete', 'pod', name, '-n', self.namespace, '--ignore-not-found', '--wait=true', '--timeout=60s', timeout=70)


def http(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        require(response.status == 200, 'HTTP distinto de 200')
        return response.read().decode()


def aws(config, service, operation, *args):
    output = command(['aws', '--region', config['region'], '--no-cli-pager', service, operation, *args, '--output', 'json'], timeout=90).stdout
    # Operaciones exitosas como ChangeMessageVisibility no devuelven payload.
    return json.loads(output) if output.strip() else {}


def order_ids(value):
    require(isinstance(value, list), 'Respuesta orders no es una lista')
    return {v['id'] for v in value}


def event_order(message):
    value = json.loads(message['Body'])
    if 'Message' in value:  # SNS envelope, si el productor lo usa en el futuro.
        value = json.loads(value['Message'])
    if 'order' in value:
        return value['order'].get('id')
    return value.get('id')


def observe_order_event(config, order_id):
    receipts = {}
    deadline = time.monotonic() + 90
    try:
        while time.monotonic() < deadline:
            messages = aws(config, 'sqs', 'receive-message', '--queue-url', config['queue_url'], '--max-number-of-messages', '10', '--wait-time-seconds', '5', '--visibility-timeout', '60').get('Messages', [])
            found = False
            for message in messages:
                receipts[message['MessageId']] = message['ReceiptHandle']
                found |= event_order(message) == order_id
            if found:
                return True
        return False
    finally:
        for receipt in receipts.values():
            aws(config, 'sqs', 'change-message-visibility', '--queue-url', config['queue_url'], '--receipt-handle', receipt, '--visibility-timeout', '0')


def full_flow(config, cluster, key, folder, persistence):
    spec = cluster.spec
    # Consultar Orders desde Checkout respeta el contrato de comunicación.
    pod = cluster.pod('checkout')
    def orders():
        return json.loads(cluster.execute(pod, 'curl', '-fsS', '--max-time', '10', 'http://orders/orders').stdout)
    before = order_ids(orders())
    receipt = folder / (key + '-purchase.json')
    env = dict(os.environ, CYPRESS_BASE_URL=spec['url'], TP_RECEIPT=str(receipt), TP_RUN_ID=uuid.uuid4().hex, TP_KUBECONFIG=str(Path(spec["kubeconfig"]).resolve()), TP_CONTEXT=spec["context"], TP_NAMESPACE=cluster.namespace, TP_RESTART="1" if persistence else "0")
    # Instalación explícita con yarn --frozen-lockfile; nunca npx descarga implícita.
    binary = ROOT / 'the-store/src/e2e/node_modules/.bin/cypress'
    require(binary.is_file(), 'Instalar las dependencias Cypress antes de --mode full')
    command_env = ['env'] + [f'{name}={env[name]}' for name in ('CYPRESS_BASE_URL', 'TP_RECEIPT', 'TP_RUN_ID', 'TP_KUBECONFIG', 'TP_CONTEXT', 'TP_NAMESPACE', 'TP_RESTART')]
    command(command_env + [str(binary), 'run', '--project', str(ROOT / 'the-store/src/e2e'), '--spec', str(ROOT / 'the-store/src/e2e/cypress/e2e/tp-compra.cy.js')], timeout=420, log=folder / (key + '-cypress.log'))
    purchase = json.loads(receipt.read_text())
    after = orders()
    require(purchase['order_id'] not in before and purchase['order_id'] in order_ids(after), 'La compra no produjo una orden nueva identificable')
    require(any(o['id'] == purchase['order_id'] and o['shippingAddress']['email'] == purchase['email'] for o in after), 'Email/ID de la compra no coinciden con Orders')
    # El productor demora 10s el envío; un mensaje previo no acorta el plazo.
    found = observe_order_event(config, purchase['order_id'])
    require(found, 'No se observó un evento SQS de la orden nueva (no se acepta un mensaje previo)')
    if persistence:
        for service in ('carts', 'checkout', 'orders'):
            cluster.run('rollout', 'restart', '-n', cluster.namespace, 'deployment/' + service)
            cluster.run('rollout', 'status', '-n', cluster.namespace, 'deployment/' + service, '--timeout=180s', timeout=190)
        pod = cluster.pod('checkout')
        require(purchase['order_id'] in order_ids(orders()), 'La orden se perdió al recrear pods')
    return {'order_id': purchase['order_id'], 'sqs_event': True, 'order_after_restart': persistence}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--mode', choices=['bootstrap', 'app', 'full'], default='app')
    parser.add_argument('--report', type=Path, default=ROOT / '.local/verificacion/report.json')
    parser.add_argument('--compare', type=Path)
    parser.add_argument('--expect', choices=['unchanged', 'rollout', 'rollback'], default='unchanged')
    parser.add_argument('--restart-for-persistence', action='store_true', help='full: recrea carts/checkout/orders y verifica la orden persistente')
    args = parser.parse_args()
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    results, snapshots, clusters = [], {}, {}
    args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    def check(name, action):
        try:
            value = action()
            results.append({'check': name, 'status': 'PASS'})
            print('PASS', name, flush=True)
            return value
        except Exception as exc:
            results.append({'check': name, 'status': 'FAIL', 'detail': str(exc)})
            print('FAIL', name, str(exc), flush=True)
            return None
    try:
        require(not args.restart_for_persistence or args.mode == 'full', '--restart-for-persistence requiere --mode full')
        config = json.loads(args.config.read_text())
        require(set(config['clusters']) == {'a', 'b'}, 'Se requieren exactamente a y b')
        for tool in ('kubectl', 'jq') + (('aws',) if args.mode != 'bootstrap' else ()):
            require(shutil.which(tool), 'Falta herramienta ' + tool)
        if args.mode != 'bootstrap':
            require(bool(config.get('region')) and set(config['alb']) >= {'url', 'target_group_arn', 'instance_ids'}, 'Falta configuración AWS/ALB')
            require(len(config['alb']['instance_ids']) == 2 and len(set(config['alb']['instance_ids'])) == 2, 'Se requieren dos EC2 diferentes para ALB')
            require(all(c.get('url') for c in config['clusters'].values()), 'Faltan URLs de ambas copias')
        if args.mode == 'full':
            require(bool(config.get('queue_url')), 'Falta queue_url')
        identities = {}
        for key, spec in config['clusters'].items():
            cluster = clusters[key] = Cluster(spec, config.get('namespace', 'the-store'))
            identity = check(key + ':bootstrap', cluster.bootstrap)
            if identity is not None:
                identities[key] = identity
        distinct = len(identities) == 2 and len(set(identities.values())) == 2
        check('identidades-distintas', lambda: require(distinct, 'APIs duplicadas o inaccesibles'))
        require(distinct, 'No se prueban ni modifican aplicaciones sin dos clústeres distintos accesibles')
        for key, cluster in clusters.items():
            identity, spec = identities[key], cluster.spec
            if args.mode != 'bootstrap':
                expected = config.get('replicas', {'ui': 2, 'catalog': 2, 'carts': 2, 'checkout': 2, 'orders': 2})
                check(key + ':replicas-readiness', lambda: cluster.application(expected))
                check(key + ':http-directo', lambda: http(spec['url'] + '/'))
                for service in ('carts', 'orders'):
                    check(key + ':credenciales:' + service, lambda s=service: cluster.credentials(s))
                for source, destination in (('ui', 'catalog'), ('ui', 'carts'), ('ui', 'checkout'), ('checkout', 'orders')):
                    check(f'{key}:{source}->{destination}', lambda s=source,d=destination: cluster.http_probe(s,d, blocked=s in config.get('quarantine', []) or d in config.get('quarantine', [])))
                check(key + ':intruso-bloqueado', cluster.stranger)
                if args.mode == 'full':
                    check(key + ':compra-orden-sqs-persistencia', lambda: full_flow(config, cluster, key, args.report.parent, args.restart_for_persistence))
            snap = ({'cluster_uid': identity, 'pods': {}, 'images': {}, 'runtime_images': {}} if args.mode == 'bootstrap'
                    else check(key + ':snapshot', cluster.snapshot))
            if snap is not None:
                snapshots[key] = snap
        if args.mode != 'bootstrap':
            check('alb:http', lambda: http(config['alb']['url'] + '/'))
            def targets():
                health = aws(config, 'elbv2', 'describe-target-health', '--target-group-arn', config['alb']['target_group_arn'])['TargetHealthDescriptions']
                require({t['Target']['Id'] for t in health} == set(config['alb']['instance_ids']), 'Targets distintos de las dos EC2 esperadas')
                require(len(health) == 2 and all(t['TargetHealth']['State'] == 'healthy' for t in health), 'Algún target del ALB no está healthy')
            check('alb:ambos-targets', targets)
        if args.compare:
            check('comparacion:' + args.expect, lambda: compare_snapshots(json.loads(args.compare.read_text())['snapshots'], snapshots, args.expect))
    except Exception as exc:
        results.append({'check': 'precondiciones', 'status': 'FAIL', 'detail': str(exc)})
    except KeyboardInterrupt:
        results.append({'check': 'interrupcion', 'status': 'FAIL'})
    finally:
        for key, cluster in clusters.items():
            check(key + ':limpieza', cluster.cleanup)
        failed = any(r['status'] == 'FAIL' for r in results)
        report = {'date': datetime.now(timezone.utc).isoformat(), 'commit': command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).stdout.strip(), 'mode': args.mode,
                  'status': 'FAIL' if failed else 'PASS', 'results': results, 'snapshots': snapshots}
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        args.report.chmod(0o600)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
