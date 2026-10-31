"""T04: acceso temporal SSM a ambos kind, con identidad y TLS verificados."""
from contextlib import AbstractContextManager
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time

from ssm import aws, run as ssm_run

ROOT = Path(__file__).resolve().parents[1]


class AccessError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise AccessError(message)


def private_write(path, content):
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
        stream.write(content)
    Path(path).chmod(0o600)


def process_start(pid):
    # starttime evita aceptar un PID reutilizado tras cerrar una sesión.
    return Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]


def process_matches(identity):
    try:
        return process_start(identity['pid']) == identity['start']
    except (OSError, KeyError, IndexError):
        return False


def invoke(args, timeout=30):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AccessError(type(exc).__name__ + '; revisar acceso kind') from exc
    # Nunca imprimir stdout/stderr: config view --raw contiene certificados privados.
    require(result.returncode == 0, f'{args[0]} falló; comprobar túneles, contexto y certificados')
    return result.stdout


def check_private(path):
    info = Path(path).lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o600,
            'Manifest/kubeconfig debe ser un archivo propio con permisos 600')


def inspect_config(path, context, port):
    check_private(path)
    value = json.loads(invoke(['kubectl', '--kubeconfig', str(path), '--context', context, 'config', 'view', '--raw', '-o', 'json']))
    require(all(len(value[k]) == 1 for k in ('clusters', 'contexts', 'users')), 'Kubeconfig debe contener exactamente un clúster/contexto/usuario')
    cluster, ctx, user = value['clusters'][0], value['contexts'][0], value['users'][0]
    require(cluster['name'] == ctx['name'] == user['name'] == context, 'Contexto kind inesperado')
    require(ctx['context']['cluster'] == ctx['context']['user'] == context, 'Contexto cruza credenciales o clústeres')
    require(cluster['cluster']['server'] == f'https://127.0.0.1:{port}', 'La API debe usar el puerto loopback acordado')
    require(cluster['cluster'].get('certificate-authority-data') and not cluster['cluster'].get('insecure-skip-tls-verify'), 'Se requiere CA y verificación TLS')
    require(not cluster['cluster'].get('proxy-url'), 'No se permite reemplazar el túnel con un proxy del kubeconfig')
    credentials = user['user']
    require(credentials.get('client-certificate-data') and credentials.get('client-key-data'), 'Faltan certificado/clave de cliente kind')
    require(not any(k in credentials for k in ('exec', 'auth-provider', 'token', 'tokenFile', 'username', 'password')), 'Solo se admite autenticación por certificado kind')


def kube(entry, *args):
    return invoke(['kubectl', '--kubeconfig', entry['kubeconfig'], '--context', entry['context'], '--request-timeout=5s', *args], timeout=15)


def validate_manifest(path):
    check_private(path)
    manifest = json.loads(Path(path).read_text())
    config = json.loads((ROOT / 'config/entorno.json').read_text())
    require(manifest.get('schema') == 1 and process_matches(manifest['owner']), 'Acceso cerrado u obsoleto; iniciar scripts/acceso.py run')
    require(set(manifest['clusters']) == {'a', 'b'}, 'Se requieren ambos clústeres a/b')
    result, uids, instances = {}, [], []
    for key in ('a', 'b'):
        entry = manifest['clusters'][key]
        expected = config['zones'][key]
        require(entry['cluster_name'] == expected['cluster_name'] and entry['context'] == 'kind-' + expected['cluster_name'], 'Destino/contexto no coincide con el contrato')
        require(entry['port'] == expected['local_api_port'] and process_matches(entry['tunnel']), 'Falta un túnel propio activo; volver a iniciar acceso')
        inspect_config(entry['kubeconfig'], entry['context'], entry['port'])
        require(kube(entry, 'get', '--raw', '/readyz').strip() == 'ok', 'API no Ready')
        uid = json.loads(kube(entry, 'get', 'namespace', 'kube-system', '-o', 'json'))['metadata']['uid']
        require(uid == entry['cluster_uid'], 'La identidad cambió respecto del destino autenticado por SSM')
        nodes = json.loads(kube(entry, 'get', 'nodes', '-o', 'json'))['items']
        require({n['metadata']['name'] for n in nodes} == {expected['cluster_name'] + '-control-plane', expected['cluster_name'] + '-worker'}, 'Nodos pertenecen a otro kind')
        check_private(entry['provider_kubeconfig'])
        result.update({f'kubeconfig_{key}': entry['provider_kubeconfig'], f'context_{key}': entry['context'], f'uid_{key}': uid})
        uids.append(uid); instances.append(entry['instance_id'])
    require(len(set(uids)) == 2 and len(set(instances)) == 2, 'A/B apuntan al mismo clúster o instancia')
    return result


REMOTE_CONFIG = '''set -eu
export PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export KUBECONFIG=/var/lib/the-store/kubeconfig
systemctl is-active --quiet the-store-kind
python3 - <<'REMOTE_PY'
import json,subprocess
from pathlib import Path
config=json.loads(Path('/opt/the-store/config.json').read_text())
uid=json.loads(subprocess.check_output(['kubectl','get','namespace','kube-system','-o','json']))['metadata']['uid']
print(json.dumps({'cluster_name':config['environment']['zones'][config['zone']]['cluster_name'], 'cluster_uid':uid, 'kubeconfig':Path('/var/lib/the-store/kubeconfig').read_text()}))
REMOTE_PY
'''


class AccessSession(AbstractContextManager):
    def __init__(self):
        self.processes, self.handles, self.logs = [], [], []
        self.folder = self.lock = None
        self.manifest_path = None

    def __enter__(self):
        try:
            local = ROOT / '.local'
            local.mkdir(exist_ok=True, mode=0o700)
            self.lock = (local / 'acceso.lock').open('a')
            os.chmod(self.lock.name, 0o600)
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise AccessError('Ya hay un acceso activo en este checkout; usar esa sesión o esperar su cierre') from exc
            self.folder = tempfile.TemporaryDirectory(prefix='acceso-', dir=local)
            folder = Path(self.folder.name)
            self.manifest_path = folder / 'manifest.json'
            config = json.loads((ROOT / 'config/entorno.json').read_text())
            self.region = config['region']
            outputs = json.loads(invoke(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json'], timeout=90))
            require('compute' in outputs and 'network' in outputs, 'Infra vacía: crear T03 y esperar bootstrap antes de abrir acceso')
            compute, network = outputs['compute']['value'], outputs['network']['value']
            require(set(compute) == {'a', 'b'}, 'Output compute debe contener a/b')
            values = aws(self.region, 'ec2', 'describe-instances', '--instance-ids', *[c['instance_id'] for c in compute.values()])['Reservations']
            instances = {i['InstanceId']: i for group in values for i in group['Instances']}
            for key in ('a', 'b'):
                instance = instances[compute[key]['instance_id']]
                require(instance['State']['Name'] == 'running' and 'PublicIpAddress' not in instance, 'El destino no es una EC2 privada running')
                require(instance['VpcId'] == network['vpc_id'] and instance['SubnetId'] == network['private_subnets'][key]['id'] and instance['PrivateIpAddress'] == compute[key]['private_ip'], 'Instancia no coincide con infraestructura actual')
                require(instance['Placement']['AvailabilityZone'] == config['zones'][key]['availability_zone'], 'AZ del destino incorrecta')
                require(instance['IamInstanceProfile']['Arn'].endswith('/' + config['iam']['instance_profile_name']), 'Perfil de instancia inesperado')
            # Reservar ambos puertos antes de crear cualquier sesión.
            ports = []
            try:
                for key in ('a', 'b'):
                    sock = socket.socket(); ports.append(sock)
                    sock.bind(('127.0.0.1', config['zones'][key]['local_api_port']))
            except OSError as exc:
                raise AccessError('Puerto local ocupado; no se reemplaza ni cierra el proceso existente') from exc
            finally:
                for sock in ports:
                    sock.close()
            manifest = {'schema': 1, 'owner': {'pid': os.getpid(), 'start': process_start(os.getpid())}, 'clusters': {}}
            for key in ('a', 'b'):
                target = compute[key]['instance_id']; zone = config['zones'][key]; port = zone['local_api_port']
                info = json.loads(ssm_run(self.region, target, REMOTE_CONFIG, folder / (key + '-remote.log'), timeout=120))
                require(info['cluster_name'] == zone['cluster_name'], 'SSM respondió desde un host con otro kind')
                old = 'server: https://127.0.0.1:' + str(config['kind']['api_port'])
                require(info['kubeconfig'].count(old) == 1, 'Endpoint remoto inesperado')
                path = folder / (key + '.kubeconfig')
                private_write(path, info['kubeconfig'].replace(old, f'server: https://127.0.0.1:{port}'))
                log = folder / (key + '-session.log'); private_write(log, '')
                handle = log.open('w'); self.handles.append(handle); self.logs.append(log)
                process = subprocess.Popen(['aws', '--region', self.region, '--no-cli-pager', 'ssm', 'start-session', '--target', target, '--document-name', 'AWS-StartPortForwardingSession', '--parameters', json.dumps({'portNumber': [str(config['kind']['api_port'])], 'localPortNumber': [str(port)]})], stdout=handle, stderr=handle, start_new_session=True)
                self.processes.append(process)
                provider_path = folder / (key + '-provider.kubeconfig')
                entry = {'instance_id': target, 'cluster_name': zone['cluster_name'], 'cluster_uid': info['cluster_uid'], 'context': 'kind-' + zone['cluster_name'], 'kubeconfig': str(path), 'provider_kubeconfig': str(provider_path), 'port': port, 'tunnel': {'pid': process.pid, 'start': process_start(process.pid)}}
                provider_config = json.loads(invoke(['kubectl', '--kubeconfig', str(path), 'config', 'view', '--raw', '-o', 'json']))
                # client-go pide credenciales al comenzar cada proceso Terraform,
                # incluso al aplicar un plan guardado o usar -refresh=false.
                # El plugin valida AMBOS destinos antes de devolver el certificado.
                provider_config['users'][0]['user'] = {'exec': {
                    'apiVersion': 'client.authentication.k8s.io/v1', 'command': sys.executable,
                    'args': [str(ROOT / 'scripts/credencial-kind.py'), str(self.manifest_path), key],
                    'interactiveMode': 'Never', 'provideClusterInfo': False,
                }}
                private_write(provider_path, json.dumps(provider_config))
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    require(process.poll() is None, 'El túnel SSM terminó al iniciar; revisar sesión/permisos del Lab')
                    try:
                        if kube(entry, 'get', '--raw', '/readyz').strip() == 'ok':
                            break
                    except AccessError:
                        pass
                    time.sleep(2)
                else:
                    raise AccessError('La API no respondió por SSM/TLS dentro del plazo')
                manifest['clusters'][key] = entry
            private_write(self.manifest_path, json.dumps(manifest))
            validate_manifest(self.manifest_path)
            return self
        except BaseException:
            self.close()
            raise

    def close(self):
        errors, session_ids = [], []
        for process in self.processes:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
        for handle in self.handles:
            handle.close()
        for log in self.logs:
            match = re.search(r'SessionId:\s*(\S+)', log.read_text())
            if match:
                session_ids.append(match.group(1))
        # Primero eliminar material privado, incluso si AWS ya no acepta la sesión.
        if self.folder is not None:
            self.folder.cleanup(); self.folder = None
        try:
            for session_id in session_ids:
                try:
                    active = aws(self.region, 'ssm', 'describe-sessions', '--state', 'Active', '--filters', json.dumps([{'key': 'SessionId', 'value': session_id}]))['Sessions']
                    if active:
                        aws(self.region, 'ssm', 'terminate-session', '--session-id', session_id)
                except Exception:
                    errors.append('No se pudo confirmar cierre de sesión remota; los túneles y certificados locales sí se retiraron')
        finally:
            if self.lock is not None:
                self.lock.close(); self.lock = None
            self.processes, self.handles, self.logs = [], [], []
        if errors:
            raise AccessError('; '.join(errors))

    def __exit__(self, *exc):
        self.close()
        return False
