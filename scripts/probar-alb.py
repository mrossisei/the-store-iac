#!/usr/bin/env python3
"""T05: valida ALB/SG reales, prueba dos kind con sondas temporales y las retira.

No despliega la aplicación T08. Rehúsa usar NodePort si ya está ocupado.
"""
from collections import Counter
from datetime import datetime, timezone
import json
import signal
import subprocess
import sys
import time
import urllib.request
import uuid

from acceso_kind import AccessSession, ROOT, kube, private_write, require
from ssm import aws

LOG = ROOT / '.local/t05'


def verify_target_set(descriptions, ids, port):
    require(len(descriptions) == 2 and {(d['Target']['Id'], d['Target']['Port']) for d in descriptions} == {(value, port) for value in ids.values()}, 'Targets no coinciden con las dos EC2 y su puerto')
    return {key: next(d['TargetHealth']['State'] for d in descriptions if d['Target']['Id'] == value) for key, value in ids.items()}


def verify_sg(groups, network, port):
    alb = groups[network['alb_security_group_id']]
    app = groups[network['application_security_group_id']]
    ingress = [{'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}], 'Ipv6Ranges': [], 'UserIdGroupPairs': [], 'PrefixListIds': []}]
    require(alb['IpPermissions'] == ingress, 'SG ALB debe permitir únicamente HTTP/80 público')
    for label, rules, target in [('salida ALB', alb['IpPermissionsEgress'], app['GroupId']), ('entrada EC2', app['IpPermissions'], alb['GroupId'])]:
        require(len(rules) == 1, label + ': se esperaba una sola regla')
        rule = rules[0]
        require(rule['IpProtocol'] == 'tcp' and rule['FromPort'] == rule['ToPort'] == port and not rule.get('IpRanges') and not rule.get('Ipv6Ranges') and not rule.get('PrefixListIds') and len(rule.get('UserIdGroupPairs', [])) == 1 and rule['UserIdGroupPairs'][0]['GroupId'] == target, label + ': el puerto solo debe conectar los SG de ALB y EC2')


def verify_aws(region, outputs, port):
    network, compute, lb = (outputs[k]['value'] for k in ('network', 'compute', 'load_balancer'))
    ids = {key: value['instance_id'] for key, value in compute.items()}
    require(lb['target_ids'] == ids and outputs['url']['value'] == 'http://' + lb['dns_name'], 'Outputs ALB/compute/URL incoherentes')
    actual = aws(region, 'elbv2', 'describe-load-balancers', '--load-balancer-arns', lb['arn'])['LoadBalancers'][0]
    require(actual['Type'] == 'application' and actual['Scheme'] == 'internet-facing' and actual['State']['Code'] == 'active' and actual['VpcId'] == network['vpc_id'] and actual['DNSName'] == lb['dns_name'], 'ALB público/activo/VPC/DNS incorrectos')
    require({a['SubnetId'] for a in actual['AvailabilityZones']} == {s['id'] for s in network['public_subnets'].values()} and actual['SecurityGroups'] == [network['alb_security_group_id']], 'Subredes o SG ALB incorrectos')
    listener = aws(region, 'elbv2', 'describe-listeners', '--listener-arns', lb['listener_arn'])['Listeners'][0]
    require(listener['LoadBalancerArn'] == lb['arn'] and listener['Protocol'] == 'HTTP' and listener['Port'] == 80 and len(listener['DefaultActions']) == 1 and listener['DefaultActions'][0]['Type'] == 'forward' and listener['DefaultActions'][0]['TargetGroupArn'] == lb['target_group_arn'], 'Listener no reenvía HTTP/80 al TG de UI')
    tg = aws(region, 'elbv2', 'describe-target-groups', '--target-group-arns', lb['target_group_arn'])['TargetGroups'][0]
    require(tg['TargetType'] == 'instance' and tg['VpcId'] == network['vpc_id'] and tg['Protocol'] == tg['HealthCheckProtocol'] == 'HTTP' and tg['Port'] == port and tg['HealthCheckPort'] == 'traffic-port' and tg['HealthCheckPath'] == '/actuator/health/readiness' and tg['Matcher']['HttpCode'] == '200' and tg['HealthCheckEnabled'], 'Target group o health check incorrectos')
    groups = aws(region, 'ec2', 'describe-security-groups', '--group-ids', network['alb_security_group_id'], network['application_security_group_id'])['SecurityGroups']
    verify_sg({g['GroupId']: g for g in groups}, network, port)
    return lb, ids


def fixture(namespace, key, run_id, port):
    labels = {'app': 't05-ui-probe', 'the-store/probe': run_id}
    command = 'mkdir -p /www/actuator/health; printf \'{"status":"UP"}\' >/www/actuator/health/readiness; printf ' + key + ':' + run_id + ' >/www/index.html; exec httpd -f -p 8080 -h /www'
    container = {
        'name': 'http', 'image': 'busybox:1.37.0', 'imagePullPolicy': 'IfNotPresent',
        'command': ['sh', '-ec', command], 'ports': [{'containerPort': 8080}],
        'readinessProbe': {'httpGet': {'path': '/actuator/health/readiness', 'port': 8080}},
    }
    metadata = {'name': 'ui-probe', 'namespace': namespace}
    return {'apiVersion': 'v1', 'kind': 'List', 'items': [
        {
            'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': metadata,
            'spec': {
                'replicas': 1, 'selector': {'matchLabels': labels},
                'template': {'metadata': {'labels': labels}, 'spec': {'containers': [container]}},
            },
        },
        {
            'apiVersion': 'v1', 'kind': 'Service', 'metadata': metadata,
            'spec': {
                'type': 'NodePort', 'selector': labels, 'externalTrafficPolicy': 'Cluster',
                'ports': [{'port': 8080, 'targetPort': 8080, 'nodePort': port}],
            },
        },
    ]}


def kube_wait(entry, *args, timeout=240):
    result = subprocess.run(['kubectl', '--kubeconfig', entry['kubeconfig'], '--context', entry['context'], '--request-timeout=15s', *args], capture_output=True, text=True, timeout=timeout)
    require(result.returncode == 0, 'kubectl no completó la sonda; revisar acceso/NodePort/readiness')
    return result.stdout


def wait_health(region, lb, ids, port, expected):
    deadline, previous = time.monotonic() + 300, None
    while time.monotonic() < deadline:
        description = aws(region, 'elbv2', 'describe-target-health', '--target-group-arn', lb['target_group_arn'])['TargetHealthDescriptions']
        states = verify_target_set(description, ids, port)
        if states != previous:
            print('Targets: ' + json.dumps(states), flush=True)
            previous = states
        if states == expected:
            return description
        time.sleep(5)
    raise RuntimeError('Targets no alcanzaron los estados esperados: ' + json.dumps(expected))


def sample_http(url, run_id, allowed, minimum=12):
    counts = Counter()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    # Cada conexión nueva permite observar ambos targets, sin cookies persistentes.
    for attempt in range(60):
        request = urllib.request.Request(url + '/?probe=' + run_id + '&n=' + str(attempt), headers={'Connection': 'close'})
        with opener.open(request, timeout=10) as response:
            require(response.status == 200, 'ALB no respondió HTTP 200')
            body = response.read(1024).decode().strip()
        key, separator, identity = body.partition(':')
        require(separator and identity == run_id and key in allowed, 'ALB respondió desde un destino ajeno/no saludable')
        counts[key] += 1
        if sum(counts.values()) >= minimum and set(counts) == set(allowed):
            return dict(counts)
        time.sleep(0.2)
    raise RuntimeError('No se observaron todos los targets saludables por HTTP')


def main():
    LOG.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_write(LOG / 'report.json', json.dumps({'status': 'RUNNING', 'date': datetime.now(timezone.utc).isoformat()}))
    config = json.loads((ROOT / 'config/entorno.json').read_text())
    outputs = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json'], timeout=90))
    region, port = config['region'], config['kind']['host_ui_port']
    lb, ids = verify_aws(region, outputs, port)
    print('PASS: ALB/listener/targets/health check/SG reales coinciden con Terraform', flush=True)
    run_id = uuid.uuid4().hex[:10]
    namespace = 't05-probe-' + run_id
    report = {'status': 'FAIL', 'date': datetime.now(timezone.utc).isoformat(), 'run_id': run_id, 'lb': lb, 'http': {}}
    with AccessSession() as access:
        entries = json.loads(access.manifest_path.read_text())['clusters']
        # Comprobar ambos antes de crear nada; no reemplazar el Service de T08.
        for entry in entries.values():
            services = json.loads(kube(entry, 'get', 'services', '-A', '-o', 'json'))['items']
            require(not any(p.get('nodePort') == config['kind']['ui_node_port'] for s in services for p in s['spec'].get('ports', [])), 'NodePort ocupado: no ejecutar sonda T05 sobre la aplicación')
        owned = {}
        try:
            for key, entry in entries.items():
                result = json.loads(kube(entry, 'create', 'namespace', namespace, '-o', 'json'))
                owned[key] = result['metadata']['uid']
                path = LOG / (key + '-fixture.json')
                private_write(path, json.dumps(fixture(namespace, key, run_id, config['kind']['ui_node_port'])))
                kube_wait(entry, 'create', '-f', str(path))
                kube_wait(entry, 'rollout', 'status', 'deployment/ui-probe', '-n', namespace, '--timeout=180s')
            report['baseline'] = wait_health(region, lb, ids, port, {'a': 'healthy', 'b': 'healthy'})
            report['http']['baseline'] = sample_http(outputs['url']['value'], run_id, {'a', 'b'})
            print('PASS: HTTP público llega a los dos kind; ambos targets healthy', flush=True)
            kube(entries['b'], 'scale', 'deployment/ui-probe', '-n', namespace, '--replicas=0')
            report['failure_b'] = wait_health(region, lb, ids, port, {'a': 'healthy', 'b': 'unhealthy'})
            report['http']['failure_b'] = sample_http(outputs['url']['value'], run_id, {'a'})
            print('PASS: al retirar la sonda B, health check falla y HTTP continúa solo por A', flush=True)
            kube(entries['b'], 'scale', 'deployment/ui-probe', '-n', namespace, '--replicas=1')
            kube_wait(entries['b'], 'rollout', 'status', 'deployment/ui-probe', '-n', namespace, '--timeout=180s')
            report['recovery'] = wait_health(region, lb, ids, port, {'a': 'healthy', 'b': 'healthy'})
            report['http']['recovery'] = sample_http(outputs['url']['value'], run_id, {'a', 'b'})
            print('PASS: B recupera health y vuelve a recibir HTTP público', flush=True)
        finally:
            errors = []
            for key, uid in owned.items():
                try:
                    current = json.loads(kube(entries[key], 'get', 'namespace', namespace, '-o', 'json'))
                    require(current['metadata']['uid'] == uid, 'Namespace reemplazado; no eliminar uno ajeno')
                    kube_wait(entries[key], 'delete', 'namespace', namespace, '--wait=true', '--timeout=90s', timeout=120)
                    require(not kube(entries[key], 'get', 'namespace', namespace, '--ignore-not-found', '-o', 'name').strip(), 'Namespace de sonda no eliminado')
                except Exception:
                    errors.append(key)
            require(not errors, 'No se pudieron retirar sondas en ' + ','.join(errors) + '; revisar antes de destruir infra')
    report['after_cleanup'] = wait_health(region, lb, ids, port, {'a': 'unhealthy', 'b': 'unhealthy'})
    report['status'] = 'PASS'
    private_write(LOG / 'report.json', json.dumps(report, indent=2) + '\n')
    print('PASS: sondas/NodePorts retirados en ambos kind y túneles cerrados; targets unhealthy sin T08', flush=True)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        private_write(LOG / 'report.json', json.dumps({'status': 'INTERRUPTED'}))
        print('Interrumpido; comprobar limpieza de sondas antes de destruir infra.', file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        if LOG.is_dir():
            private_write(LOG / 'report.json', json.dumps({'status': 'FAIL', 'error': str(exc)}))
        print('FALLA T05: ' + str(exc), file=sys.stderr)
        sys.exit(1)
