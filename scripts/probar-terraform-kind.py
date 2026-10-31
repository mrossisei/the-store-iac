#!/usr/bin/env python3
"""T04 integración real: crea/lee/actualiza, prueba fallos y destruye SOLO los probes.

Requiere infra T03 lista y backend aplicacion inicializado. No crea/destruye EC2.
No usar sobre un estado que ya contenga la aplicación T08.
"""
from collections import Counter
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from acceso_kind import AccessSession, ROOT, kube, private_write, require
from ssm import aws

LOG = ROOT / '.local/t04'
APP = ROOT / 'terraform/aplicacion'
checks = []


def passed(message):
    checks.append(message)
    print('PASS: ' + message, flush=True)


def tf(access, label, *args, fail=False):
    env = dict(os.environ, TF_VAR_access_manifest=str(access.manifest_path), TF_VAR_enable_access_probe='true', TF_VAR_probe_value='updated', TF_IN_AUTOMATION='1')
    command = ['terraform', '-chdir=' + str(APP), *args]
    result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=600)
    private_write(LOG / (label + '.log'), result.stdout + result.stderr)
    if fail:
        diagnostic = result.stdout + result.stderr
        require(result.returncode != 0 and ('Acceso kind inválido' in diagnostic or 'getting credentials: exec:' in diagnostic), label + ': se esperaba rechazo del guard de acceso')
    else:
        require(result.returncode == 0, label + ': Terraform falló; diagnóstico privado en ' + str(LOG))
    return result.stdout


def plan(access, label, action_counts, *extra):
    path = LOG / (label + '.tfplan')
    tf(access, label, 'plan', '-input=false', '-no-color', '-out=' + str(path), *extra)
    value = json.loads(tf(access, label + '-json', 'show', '-json', str(path)))
    changes = [c for c in value.get('resource_changes', []) if c['mode'] == 'managed' and c['change']['actions'] != ['no-op']]
    require(all(c['address'].startswith(('module.probe_a[0].', 'module.probe_b[0].')) for c in changes), 'Plan toca recursos ajenos al probe T04')
    require(Counter(tuple(c['change']['actions']) for c in changes) == Counter(action_counts), 'Cambios inesperados en ' + label)
    return path


def read_probes(access, expected):
    manifest = json.loads(access.manifest_path.read_text())
    for key, entry in manifest['clusters'].items():
        actual = json.loads(kube(entry, 'get', 'configmap', 'access-proof', '-n', 'the-store-t04-probe', '-o', 'json'))['data']
        require(actual == {'cluster': key, 'cluster_uid': entry['cluster_uid'], 'value': expected}, 'Objeto escrito/leído en destino incorrecto: ' + key)


def main():
    LOG.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(LOG, 0o700)
    inventory = subprocess.run(['terraform', '-chdir=' + str(APP), 'state', 'list'], text=True, capture_output=True, timeout=90)
    require(inventory.returncode == 0 or 'No state file was found!' in inventory.stderr, 'No se pudo inventariar estado app; no operar')
    state = inventory.stdout if inventory.returncode == 0 else ''
    require(not any(line and not line.startswith('data.') for line in state.splitlines()), 'Estado app no vacío; no ejecutar prueba destructiva sobre T08/probes previos')
    with AccessSession() as access:
        manifest = json.loads(access.manifest_path.read_text())
        try:
            with AccessSession():
                raise RuntimeError('Aceptó dos administradores en un checkout')
        except Exception as exc:
            require('Ya hay un acceso activo' in str(exc), 'Bloqueo de acceso no funcionó')
        passed('segunda sesión del checkout rechazada sin cerrar los túneles existentes')
        config = LOG / 'bootstrap-config.json'
        private_write(config, json.dumps({'clusters': {key: {'kubeconfig': entry['kubeconfig'], 'context': entry['context']} for key, entry in manifest['clusters'].items()}}))
        result = subprocess.run([str(ROOT / 'verificar.sh'), '--config', str(config), '--mode', 'bootstrap', '--report', str(LOG / 'bootstrap-report.json')], capture_output=True, text=True, timeout=240)
        private_write(LOG / 'bootstrap.log', result.stdout + result.stderr)
        require(result.returncode == 0 and json.loads((LOG / 'bootstrap-report.json').read_text())['status'] == 'PASS', 'Arnés T10 bootstrap falló')
        passed('arnés T10 bootstrap sobre ambas API por SSM/TLS')
        # La identidad mal declarada debe fallar antes de llegar al provider.
        original = access.manifest_path.read_text()
        manifest['clusters']['b']['cluster_uid'] = manifest['clusters']['a']['cluster_uid']
        private_write(access.manifest_path, json.dumps(manifest))
        tf(access, 'rejected-identity', 'plan', '-input=false', '-no-color', fail=True)
        private_write(access.manifest_path, original)
        passed('identidad A/B cruzada rechazada antes de operar')
        created = plan(access, 'create', {('create',): 4}, '-var=probe_value=initial')
        tf(access, 'apply-create', 'apply', '-input=false', '-no-color', str(created))
        read_probes(access, 'initial')
        passed('Terraform creó y API leyó namespace/ConfigMap en cada kind')
        updated = plan(access, 'update', {('update',): 2})
        tf(access, 'apply-update', 'apply', '-input=false', '-no-color', str(updated))
        read_probes(access, 'updated')
        plan(access, 'converged', {})
        passed('actualización de ambos ConfigMaps y segundo plan sin cambios')
        # Plan guardado no vuelve a leer data.external: exec debe protegerlo.
        forbidden = plan(access, 'forbidden', {('update',): 2}, '-var=probe_value=forbidden')
        process = access.processes[1]
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=20)
        tf(access, 'rejected-plan', 'plan', '-input=false', '-no-color', fail=True)
        tf(access, 'rejected-saved-apply', 'apply', '-input=false', '-no-color', str(forbidden), fail=True)
        tf(access, 'rejected-destroy', 'destroy', '-input=false', '-no-color', '-auto-approve', '-refresh=false', fail=True)
        # A sigue accesible: ni apply ni destroy pueden cambiarla si falta B.
        a = json.loads(access.manifest_path.read_text())['clusters']['a']
        actual = json.loads(kube(a, 'get', 'configmap', 'access-proof', '-n', 'the-store-t04-probe', '-o', 'json'))['data']
        require(actual['value'] == 'updated', 'Se operó A con B caída')
        passed('sin túnel B: plan, apply guardado y destroy rechazados; A intacta')
    require(not access.manifest_path.exists(), 'No se limpiaron certificados/manifest')
    with AccessSession() as access:
        read_probes(access, 'updated')
        passed('al reabrir acceso, A y B conservan el último valor válido')
        # Ninguna clave/certificado debe estar en JSON de plan/estado.
        state = tf(access, 'state', 'state', 'pull')
        for entry in json.loads(access.manifest_path.read_text())['clusters'].values():
            raw = subprocess.check_output(['kubectl', '--kubeconfig', entry['kubeconfig'], 'config', 'view', '--raw', '-o', 'json'], text=True)
            credentials = json.loads(raw)['users'][0]['user']
            for value in credentials.values():
                require(value not in state and all(value not in p.read_text() for p in LOG.glob('*-json.log')), 'Credenciales presentes en estado/plan')
        passed('estado y planes contienen paths/UID, sin certificados ni claves')
        deleted = plan(access, 'delete', {('delete',): 4}, '-destroy')
        tf(access, 'apply-delete', 'apply', '-input=false', '-no-color', str(deleted))
        for entry in json.loads(access.manifest_path.read_text())['clusters'].values():
            require(not kube(entry, 'get', 'namespace', 'the-store-t04-probe', '--ignore-not-found', '-o', 'name').strip(), 'Namespace de prueba sobrevivió a destroy')
        passed('destroy de app eliminó los objetos en ambos kind')
        ids = [e['instance_id'] for e in json.loads(access.manifest_path.read_text())['clusters'].values()]
        instances = aws(access.region, 'ec2', 'describe-instances', '--instance-ids', *ids)['Reservations']
        require(all(i['State']['Name'] == 'running' for group in instances for i in group['Instances']), 'Destroy app modificó EC2')
        passed('ambas EC2 siguen running después de destroy app')
    require(not access.manifest_path.exists(), 'Material privado no retirado')
    passed('túneles y kubeconfigs temporales retirados')
    private_write(LOG / 'report.json', json.dumps({'status': 'PASS', 'checks': checks}, indent=2) + '\n')


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        print('Interrumpido; revisar estado app antes de retirar infra.', file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print('FALLA T04: ' + str(exc) + '; revisar app antes de retirar infra.', file=sys.stderr)
        sys.exit(1)
