#!/usr/bin/env python3
"""T09: sondas sobre los pods reales, sin crear/reiniciar/reetiquetar objetos."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlsplit

from acceso_kind import validate_manifest
from verificar import Cluster, CheckError, curl_result, ready, require

ROOT = Path(__file__).resolve().parents[1]
APPS = ('ui', 'catalog', 'carts', 'checkout', 'orders')
HEALTH = {app: '/health' if app in ('catalog', 'checkout') else '/actuator/health/readiness' for app in APPS}
NODE_PROBE = (ROOT / 'scripts/probes/politicas.js').read_text()


def private_json(path, value):
    path = Path(path)
    require('.local' in path.resolve().parts, 'Evidencia debe guardarse bajo .local')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
    path.chmod(0o600)


def template_hashes(cluster):
    return {d['metadata']['name']: hashlib.sha256(json.dumps(d['spec']['template'], sort_keys=True).encode()).hexdigest()
            for d in cluster.get('deployments', '-n', cluster.namespace)['items'] if d['metadata']['name'] in APPS}


def identity(cluster):
    snapshot = cluster.snapshot()
    snapshot['templates'] = template_hashes(cluster)
    return snapshot


def compare(before, after):
    for field in ('cluster_uid', 'pods', 'images', 'templates'):
        require(before[field] == after[field], 'Cambió identidad/UID/restarts/PodTemplate: ' + field)


def check_probe(value, blocked):
    require(isinstance(value, dict) and value.get('status') == ('timeout' if blocked else 'ok'),
            'Sonda inválida o expectativa incorrecta: ' + json.dumps(value))


def node_probe(cluster, pod, kind, host, port=0):
    # JS and all arguments are separate argv entries; no shell interpolation.
    result = cluster.execute(pod, 'node', '-e', NODE_PROBE, kind, host, str(port), timeout=15)
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        raise CheckError('Node no devolvió JSON de sonda') from exc


def app_pods(cluster, phase):
    result = {}
    for app in APPS:
        pods = cluster.get('pods', '-n', cluster.namespace, '-l', 'app=' + app)['items']
        pods = [p for p in pods if not p['metadata'].get('deletionTimestamp')]
        deployment = cluster.get('deployment', app, '-n', cluster.namespace)
        require(len(pods) == deployment['spec']['replicas'] and bool(pods), app + ': conteo de pods incorrecto')
        for pod in pods:
            require(pod['status'].get('phase') == 'Running' and pod['status'].get('podIP'), app + ': pod no Running/IP')
            require(all(c.get('state', {}).get('running') for c in pod['status'].get('containerStatuses', [])), app + ': contenedor no ejecutándose')
            if phase != 'quarantine' or app != 'checkout':
                require(ready([pod], 1), app + ': pod no Ready')
        result[app] = pods
    return result


def canonical(value):
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted([canonical(v) for v in value], key=lambda v: json.dumps(v, sort_keys=True))
    return value


def expected_policies(phase, nodes, pod_cidr, service_cidr):
    active = set(APPS) - ({'checkout'} if phase == 'quarantine' else set())
    flows = [('ui', app) for app in ('catalog', 'carts', 'checkout')] + [('checkout', 'orders')]
    flows = [(a, b) for a, b in flows if a in active and b in active]
    selector = lambda app: {'matchLabels': {'app': app}}
    cluster_cidrs = [pod_cidr, service_cidr]
    outside = {'ipBlock': {'cidr': '0.0.0.0/0', 'except': cluster_cidrs}}
    port = [{'port': 8080, 'protocol': 'TCP'}]
    expected = {'default-deny': {'podSelector': {}, 'policyTypes': ['Ingress', 'Egress']}}
    for source, destination in flows:
        name = 'allow-' + source + '-' + destination
        expected[name] = {'podSelector': selector(destination), 'policyTypes': ['Ingress'],
                          'ingress': [{'from': [{'podSelector': selector(source)}], 'ports': port}]}
        expected[name + '-egress'] = {'podSelector': selector(source), 'policyTypes': ['Egress'],
                                     'egress': [{'to': [{'podSelector': selector(destination)}], 'ports': port}]}
    for app in active:
        expected['allow-' + app + '-external'] = {
            'podSelector': selector(app), 'policyTypes': ['Egress'], 'egress': [
                {'to': [outside]}, {'to': [{'namespaceSelector': {'matchLabels': {'kubernetes.io/metadata.name': 'kube-system'}},
                                          'podSelector': {'matchLabels': {'k8s-app': 'kube-dns'}}}],
                                    'ports': [{'port': 53, 'protocol': protocol} for protocol in ('UDP', 'TCP')]}]}
    ips = set()
    for node in nodes:
        ips.update(a['address'] for a in node['status']['addresses'] if a['type'] == 'InternalIP' and ':' not in a['address'])
        annotations = node['metadata'].get('annotations', {})
        ips.update(annotations[key] for key in ('projectcalico.org/IPv4IPIPTunnelAddr', 'projectcalico.org/IPv4VXLANTunnelAddr') if annotations.get(key))
    expected['allow-ui-nodeport'] = {'podSelector': selector('ui'), 'policyTypes': ['Ingress'],
                                     'ingress': [{'from': [outside] + [{'ipBlock': {'cidr': ip + '/32'}} for ip in sorted(ips)], 'ports': port}]}
    return expected


def validate_policies(policies, expected):
    actual = {p['metadata']['name']: p['spec'] for p in policies}
    require(canonical(actual) == canonical(expected), 'Policies extra/faltantes o reglas alternativas; revisar allows aditivos y fase')
    return actual


def audit_policies(cluster, phase):
    # Fail closed on unmanaged or broadened policies: Kubernetes adds allows
    # across all policies, so matching only the names would be insufficient.
    env = json.loads((ROOT / 'config/entorno.json').read_text())
    nodes = cluster.get('nodes')['items']
    expected = expected_policies(phase, nodes, env['kind']['pod_cidr'], env['kind']['service_cidr'])
    return validate_policies(cluster.get('networkpolicies', '-n', cluster.namespace)['items'], expected)


def run_cluster(entry, namespace, phase, before, evidence):
    cluster = Cluster(entry, namespace)
    evidence['before'] = identity(cluster)
    if before:
        compare(before['before'], evidence['before'])
    # Policy API updates precede asynchronous Calico dataplane programming.
    time.sleep(3)
    pods = app_pods(cluster, phase)
    evidence['policies'] = audit_policies(cluster, phase)
    evidence['checks'] = []
    def record(name, function):
        item = {'name': name, 'status': 'FAIL'}
        evidence['checks'].append(item)
        function()
        item['status'] = 'PASS'
    def http(source, target, blocked):
        result = cluster.execute(source['metadata']['name'], 'curl', '--noproxy', '*', '-sS', '--connect-timeout', '3', '--max-time', '4', '-o', '/dev/null', '-w', '%{http_code}', target, allowed=tuple(range(256)), timeout=15)
        curl_result(result, blocked)
        if not blocked:
            require(result.stdout.strip() == '200', 'Endpoint de salud no devuelve HTTP200')
    # Loopback establishes effective tooling and actual destination process even
    # when readiness removes Checkout from Service endpoints during quarantine.
    for app in ('ui', 'checkout', 'carts', 'orders'):
        for pod in pods[app]:
            cluster.execute(pod['metadata']['name'], 'curl', '--version')
            result = cluster.execute(pod['metadata']['name'], 'curl', '--noproxy', '*', '-sS', '--max-time', '3', '-o', '/dev/null', '-w', '%{http_code}', 'http://127.0.0.1:8080' + HEALTH[app], allowed=tuple(range(256)))
            curl_result(result)
    flows = [('ui', app) for app in ('catalog', 'carts', 'checkout')] + [('checkout', 'orders')]
    forbidden = [('ui', 'orders'), ('carts', 'orders'), ('orders', 'checkout'), ('checkout', 'catalog'), ('checkout', 'carts')]
    for source, destination in flows + forbidden:
        blocked = (source, destination) in forbidden or (phase == 'quarantine' and 'checkout' in (source, destination))
        for src in pods[source]:
            for dst in pods[destination]:
                target = 'http://' + dst['status']['podIP'] + ':8080' + HEALTH[destination]
                name = src['metadata']['name'] + '→' + dst['metadata']['name'] + (' blocked' if blocked else ' allowed')
                record(name, lambda src=src, target=target, blocked=blocked: http(src, target, blocked))
    if before:
        destinations = before['destinations']
    else:
        checkout = cluster.get('deployment', 'checkout', '-n', namespace)
        env = {e['name']: e.get('value', '') for c in checkout['spec']['template']['spec']['containers'] for e in c.get('env', [])}
        redis = urlsplit(env.get('RETAIL_CHECKOUT_PERSISTENCE_REDIS_URL', ''))
        require(redis.scheme == 'redis' and redis.hostname and not redis.password, 'Redis debe usar el endpoint configurado sin credenciales')
        resolver = pods['checkout'][0]['metadata']['name']
        addresses = node_probe(cluster, resolver, 'resolve', redis.hostname)
        check_probe(addresses, False)
        internet = node_probe(cluster, resolver, 'resolve', 'example.com')
        check_probe(internet, False)
        dns = cluster.get('service', 'kube-dns', '-n', 'kube-system')['spec']['clusterIP']
        destinations = {'redis_host': redis.hostname, 'redis_ips': addresses['addresses'], 'redis_port': redis.port or 6379, 'dns_ip': dns, 'internet_ip': internet['addresses'][0], 'internet_port': 443}
    evidence['destinations'] = destinations
    for pod in pods['checkout']:
        source = pod['metadata']['name']
        for kind, host, port in [('redis', ip, destinations['redis_port']) for ip in destinations['redis_ips']] + [
                ('dns-udp', destinations['dns_ip'], 53), ('dns-tcp', destinations['dns_ip'], 53),
                ('tcp', destinations['internet_ip'], destinations['internet_port'])]:
            def probe(source=source, kind=kind, host=host, port=port):
                value = node_probe(cluster, source, kind, host, port)
                check_probe(value, phase == 'quarantine')
            record(source + '→' + kind + ':' + host, probe)
    # Controls use unquarantined UI. A fresh curl process resolves the Service
    # name via normal DNS; numeric TCP controls check exact external endpoints.
    ui = pods['ui'][0]
    record('UI DNS + catalog health', lambda: http(ui, 'http://catalog' + HEALTH['catalog'], False))
    for host, port in [(destinations['dns_ip'], 53), (destinations['internet_ip'], destinations['internet_port'])] + [(ip, destinations['redis_port']) for ip in destinations['redis_ips']]:
        # Bash opens a TCP socket without sending application bytes. Both Bash
        # and timeout are present in the existing AL2023 UI image. No telnet
        # protocol support or extra container install is assumed.
        cluster.execute(ui['metadata']['name'], 'timeout', '4', 'bash', '-c',
                        'exec 3<>/dev/tcp/"$1"/"$2"', 't09-control', host, str(port), timeout=10)
        evidence['checks'].append({'name': 'UI control TCP ' + host + ':' + str(port), 'status': 'PASS'})
    evidence['after'] = identity(cluster)
    compare(evidence['before'], evidence['after'])


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', default=os.environ.get('THE_STORE_ACCESS_MANIFEST'))
    parser.add_argument('--phase', required=True, choices=['baseline', 'quarantine', 'restored'])
    parser.add_argument('--evidence', required=True)
    parser.add_argument('--baseline')
    parser.add_argument('--namespace', default='the-store')
    args = parser.parse_args()
    report = {'schema': 1, 'phase': args.phase, 'time': datetime.now(timezone.utc).isoformat(), 'status': 'FAIL', 'clusters': {}}
    try:
        require(bool(args.manifest), 'Usar acceso.py run o --manifest temporal')
        require(args.phase == 'baseline' or bool(args.baseline), 'Cuarentena/reversión requiere --baseline')
        baseline = json.loads(Path(args.baseline).read_text()) if args.baseline else None
        if baseline:
            require(baseline.get('status') == 'PASS' and baseline.get('phase') == 'baseline', 'Baseline no aprobada')
        validate_manifest(args.manifest)
        manifest = json.loads(Path(args.manifest).read_text())
        for key in ('a', 'b'):
            evidence = report['clusters'][key] = {}
            run_cluster(manifest['clusters'][key], args.namespace, args.phase, baseline['clusters'][key] if baseline else None, evidence)
        report['status'] = 'PASS'
    except Exception as exc:
        # Do not dump subprocess output, environment, PodSpec or access material.
        report['error'] = str(exc) if isinstance(exc, CheckError) else type(exc).__name__
    private_json(args.evidence, report)
    print(report['status'] + ': T09 ' + args.phase + '; evidencia ' + args.evidence)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
