#!/usr/bin/env python3
"""T03: EC2 privadas, bootstrap real, repetición y recuperación tras reboot."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

from ssm import aws, run, SSMError

ROOT = Path(__file__).resolve().parents[1]

WAIT = '''
set -eu
export PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export KUBECONFIG=/var/lib/the-store/kubeconfig
timeout 2200 bash -c 'until systemctl is-active --quiet the-store-kind; do
  if systemctl is-failed --quiet the-store-kind; then journalctl -u the-store-kind -n 70 --no-pager; exit 1; fi
  sleep 10
done'
'''
SUMMARY = '''
python3 - <<'PY_SUMMARY'
import json,subprocess
from pathlib import Path
def kubectl(*args): return json.loads(subprocess.check_output(['kubectl',*args,'-o','json']))
s=json.loads(Path('/var/lib/the-store/status.json').read_text())
s['cluster_uid']=kubectl('get','namespace','kube-system')['metadata']['uid']
s['node_uids']={n['metadata']['name']:n['metadata']['uid'] for n in kubectl('get','nodes')['items']}
s['container_ids']=sorted(subprocess.check_output(['docker','ps','-aq','--filter','label=io.x-k8s.kind.cluster='+s['cluster']],text=True).splitlines())
s['aws_cli']=subprocess.check_output(['aws','--version'],text=True).strip()
s['kubernetes']=kubectl('version','--client')['clientVersion']['gitVersion']
s['boot_id']=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
s['memory_kib']=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemTotal:')))
print('T03_RESULT='+json.dumps(s,separators=(',',':')))
PY_SUMMARY
'''
PROBE = WAIT + '''
BEFORE=$(kubectl get namespace kube-system -o jsonpath='{.metadata.uid}')
CONTAINERS=$(docker ps -aq --filter "label=io.x-k8s.kind.cluster=$(jq -r .cluster /var/lib/the-store/status.json)" | sort)
/opt/the-store/smoke.sh
systemctl restart the-store-kind
[ "$BEFORE" = "$(kubectl get namespace kube-system -o jsonpath='{.metadata.uid}')" ]
[ "$CONTAINERS" = "$(docker ps -aq --filter "label=io.x-k8s.kind.cluster=$(jq -r .cluster /var/lib/the-store/status.json)" | sort)" ]
''' + SUMMARY
POSTBOOT = WAIT + '''
kubectl wait --for=condition=Ready nodes --all --timeout=180s
/opt/the-store/smoke.sh
''' + SUMMARY


def parse_summary(output):
    lines = [line.removeprefix('T03_RESULT=') for line in output.splitlines() if line.startswith('T03_RESULT=')]
    if len(lines) != 1:
        raise SSMError('Falta un único resumen remoto verificable')
    result = json.loads(lines[0])
    if result['status'] != 'PASS' or len(result['node_uids']) != 2 or len(result['container_ids']) != 2 or result['memory_kib'] < 7_000_000:
        raise SSMError('Resumen remoto no cumple capacidad/dos nodos')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reboot', action='store_true', help='reinicia las dos EC2 propias y verifica recuperación')
    parser.add_argument('--report', type=Path, default=ROOT / '.local/t03-report.json')
    args = parser.parse_args()
    config = json.loads((ROOT / 'config/entorno.json').read_text())
    compute = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json', 'compute'], timeout=90))
    network = json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json', 'network'], timeout=90))
    tools = json.loads((ROOT / 'config/herramientas.json').read_text())
    region = config['region']
    summaries, failures = {}, []
    try:
        reservations = aws(region, 'ec2', 'describe-instances', '--instance-ids', *[v['instance_id'] for v in compute.values()])['Reservations']
        instances = {i['InstanceId']: i for r in reservations for i in r['Instances']}
        for key, value in compute.items():
            instance = instances[value['instance_id']]
            assert instance['ImageId'] == tools['ec2_ami_id'] and instance['InstanceType'] == tools['instance_type_candidate']
            assert 'PublicIpAddress' not in instance and instance['SubnetId'] == network['private_subnets'][key]['id']
            assert instance['Placement']['AvailabilityZone'] == config['zones'][key]['availability_zone']
            assert instance['IamInstanceProfile']['Arn'].endswith('/' + config['iam']['instance_profile_name'])
            assert {s['GroupId'] for s in instance['SecurityGroups']} == {network['application_security_group_id']}
            assert instance['MetadataOptions']['HttpTokens'] == 'required' and instance['MetadataOptions']['HttpPutResponseHopLimit'] == 3
        print('PASS: dos EC2 privadas por AZ, perfil/SG e IMDSv2 correctos', flush=True)
        def probe(key):
            deadline = time.monotonic() + 600
            instance = compute[key]['instance_id']
            while time.monotonic() < deadline:
                info = aws(region, 'ssm', 'describe-instance-information', '--filters', 'Key=InstanceIds,Values=' + instance)['InstanceInformationList']
                if any(i['PingStatus'] == 'Online' for i in info):
                    break
                time.sleep(5)
            else:
                raise SSMError(key + ': SSM no Online')
            value = parse_summary(run(region, instance, PROBE, args.report.parent / ('t03-' + key + '.log')))
            print('PASS: ' + key + ' bootstrap, NodePort, Calico y repetición sin reemplazos', flush=True)
            return key, value
        with ThreadPoolExecutor(max_workers=2) as pool:
            for key, value in pool.map(probe, compute):
                summaries[key] = value
        assert len({v['cluster_uid'] for v in summaries.values()}) == 2, 'Los kind no son independientes'
        if args.reboot:
            aws(region, 'ec2', 'reboot-instances', '--instance-ids', *[v['instance_id'] for v in compute.values()])
            time.sleep(20)
            def recovered(key):
                deadline = time.monotonic() + 600
                while time.monotonic() < deadline:
                    try:
                        after = parse_summary(run(region, compute[key]['instance_id'], POSTBOOT, args.report.parent / ('t03-' + key + '-reboot.log'), timeout=600))
                        if after['boot_id'] != summaries[key]['boot_id']:
                            assert after['cluster_uid'] == summaries[key]['cluster_uid']
                            assert after['node_uids'] == summaries[key]['node_uids']
                            assert after['container_ids'] == summaries[key]['container_ids']
                            print('PASS: ' + key + ' reboot recupera kind/Calico/NodePort conservando identidad', flush=True)
                            return key, after
                    except SSMError as exc:
                        if str(exc) not in ('InvalidInstanceId', 'TargetNotConnected'):
                            raise
                    time.sleep(10)
                raise SSMError(key + ': no se comprobó recuperación de otro arranque')
            with ThreadPoolExecutor(max_workers=2) as pool:
                for key, value in pool.map(recovered, compute):
                    summaries[key]['after_reboot'] = value
    except KeyboardInterrupt:
        failures.append('Verificación interrumpida')
        print('FAIL: verificación interrumpida', flush=True)
    except Exception as exc:
        failures.append(str(exc) or type(exc).__name__)
        print('FAIL:', failures[-1], flush=True)
    finally:
        args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        args.report.write_text(json.dumps({'date': datetime.now(timezone.utc).isoformat(), 'status': 'FAIL' if failures else 'PASS', 'reboot_tested': args.reboot and not failures, 'clusters': summaries, 'failures': failures}, indent=2) + '\n')
        args.report.chmod(0o600)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
