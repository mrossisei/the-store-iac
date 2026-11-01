#!/usr/bin/env python3
"""T06: topología AWS y datos compartidos desde EC2 A/B; limpia únicamente sus sondas."""
import base64
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import uuid

from acceso_kind import AccessError, ROOT, private_write, require
from datos_topologia import verify
from ssm import SSMError, aws, run

LOG = ROOT / '.local/t06'


def backend_bucket(metadata, expected_key):
    backend = metadata.get('backend', {})
    config = backend.get('config', {})
    require(backend.get('type') == 's3' and config.get('key') == expected_key and config.get('encrypt') is True and config.get('use_lockfile') is True and config.get('bucket'), 'Inicializar backend S3 kind cifrado/con lock antes de la sonda')
    return config['bucket']


def remove_config_versions(region, bucket, key, account, version=None):
    if version is not None:
        aws(region, 's3api', 'delete-object', '--bucket', bucket, '--key', key, '--version-id', version, '--expected-bucket-owner', account)
    # Incluye uploads cuya respuesta se perdió; nunca borra otra key/estado.
    remaining = aws(region, 's3api', 'list-object-versions', '--bucket', bucket, '--prefix', key)
    for value in remaining.get('Versions', []) + remaining.get('DeleteMarkers', []):
        if value['Key'] == key:
            aws(region, 's3api', 'delete-object', '--bucket', bucket, '--key', key, '--version-id', value['VersionId'], '--expected-bucket-owner', account)
    remaining = aws(region, 's3api', 'list-object-versions', '--bucket', bucket, '--prefix', key)
    require(not any(value['Key'] == key for value in remaining.get('Versions', []) + remaining.get('DeleteMarkers', [])), 'Versión privada de sonda no retirada')


def terraform_values():
    result = subprocess.run(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json'], capture_output=True, text=True, timeout=90)
    require(result.returncode == 0, 'No se pudieron leer outputs de infra')
    return {key: value['value'] for key, value in json.loads(result.stdout).items()}


def parse_result(output, phase):
    lines = [line.removeprefix('T06_RESULT=') for line in output.splitlines() if line.startswith('T06_RESULT=')]
    require(len(lines) == 1, 'Falta un único resultado verificable de datos')
    result = json.loads(lines[0])
    require(result.get('status') == 'PASS' and result.get('phase') == phase and result.get('credential_method') == 'iam-role' and result.get('role') == 'LabRole' and result.get('sql_tls_verified') is True and result.get('checks'), 'Resultado remoto no certifica fase, TLS o LabRole')
    expected = {
        'seed': {'mysql-write-a', 'postgres-write-a', 'redis-write-a', 'dynamo-write-a', 'sqs-send-a'},
        'read-b-write': {'mysql-cross-a-b', 'postgres-cross-a-b', 'redis-primary-reader-cross-a-b', 'dynamo-gsi-cross-a-b', 'sqs-cross-a-b'},
        'read-a': {'mysql-cross-b-a', 'postgres-cross-b-a', 'redis-replication-cross-b-a', 'dynamo-cross-b-a', 'sqs-cross-b-a'},
        'cleanup': {'sql-probe-tables-removed', 'redis-dynamo-probe-keys-removed', 'owned-sqs-messages-removed'},
    }
    require(set(result['checks']) == expected[phase], 'Resultado parcial no demuestra los cinco servicios de datos')
    return result


def main():
    LOG.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_write(LOG / 'report.json', json.dumps({'status': 'RUNNING'}))
    values = terraform_values()
    environment = json.loads((ROOT / 'config/entorno.json').read_text())
    tools = json.loads((ROOT / 'config/herramientas.json').read_text())
    region = environment['region']
    topology = verify(values, environment, tools)
    print('PASS: topología RDS/Redis Multi-AZ y SG/esquemas reales comprobados', flush=True)
    run_id = uuid.uuid4().hex[:24]
    require(re.fullmatch('[0-9a-f]{24}', run_id), 'ID inválido')
    metadata = json.loads((ROOT / 'terraform/infra/.terraform/terraform.tfstate').read_text())
    bucket = backend_bucket(metadata, environment['state_keys']['infra'])
    account = aws(region, 'sts', 'get-caller-identity')['Account']
    key = 'scratch/t06/' + run_id + '/connection.json'
    connection_file = LOG / ('connection-' + run_id + '.json')
    folder = '/var/lib/the-store/t06-probe-' + run_id
    code = base64.b64encode((ROOT / 'scripts/probes/datos.py').read_bytes()).decode()
    requirements = base64.b64encode((ROOT / 'scripts/probes/requirements-datos.txt').read_bytes()).decode()
    version, upload_attempted = None, False
    owned, phases, errors = [], [], []
    summary = {'status': 'FAIL', 'date': datetime.now(timezone.utc).isoformat(), 'run_id': run_id, 'topology': topology, 'phases': phases}
    try:
        private_write(connection_file, json.dumps({'run_id': run_id, 'region': region, 'connection': values['databases'], 'redis_reader_host': values['data_resources']['redis_reader_host']}))
        require(aws(region, 's3api', 'get-bucket-versioning', '--bucket', bucket)['Status'] == 'Enabled', 'Bucket de estado debe conservar versionado')
        previous = aws(region, 's3api', 'list-object-versions', '--bucket', bucket, '--prefix', key)
        require(not any(v['Key'] == key for v in previous.get('Versions', []) + previous.get('DeleteMarkers', [])), 'La key temporal ya existía; no adoptarla')
        upload_attempted = True
        try:
            version = aws(region, 's3api', 'put-object', '--bucket', bucket, '--key', key, '--body', str(connection_file), '--server-side-encryption', 'AES256', '--if-none-match', '*', '--expected-bucket-owner', account)['VersionId']
        except SSMError as exc:
            if str(exc) in ('PreconditionFailed', '412'):
                upload_attempted = False  # una escritura concurrente ajena
            raise
        # Solo el objeto S3 cifrado lleva passwords; Run Command contiene paths/código.
        def setup(name):
            script = f'''set -eu
umask 077
export PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
test ! -e {shlex.quote(folder)}
mkdir -m 700 {shlex.quote(folder)}
printf %s {shlex.quote(run_id)} >{shlex.quote(folder)}/owner
dnf install -y python3.11 python3.11-pip >/dev/null
python3.11 -m venv {shlex.quote(folder)}/venv
printf %s {shlex.quote(code)} | base64 -d >{shlex.quote(folder)}/client.py
printf %s {shlex.quote(requirements)} | base64 -d >{shlex.quote(folder)}/requirements.txt
PIP_CONFIG_FILE=/dev/null {shlex.quote(folder)}/venv/bin/pip --disable-pip-version-check install -q --index-url https://pypi.org/simple -r {shlex.quote(folder)}/requirements.txt
aws --region {shlex.quote(region)} s3api get-object --bucket {shlex.quote(bucket)} --key {shlex.quote(key)} --version-id {shlex.quote(version)} --expected-bucket-owner {shlex.quote(account)} {shlex.quote(folder)}/connection.json >/dev/null
curl -fsSL --retry 3 https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o {shlex.quote(folder)}/rds-ca.pem
chmod 600 {shlex.quote(folder)}/client.py {shlex.quote(folder)}/connection.json {shlex.quote(folder)}/requirements.txt {shlex.quote(folder)}/rds-ca.pem {shlex.quote(folder)}/owner
echo SETUP_OK
'''
            output = run(region, values['compute'][name]['instance_id'], script, LOG / (name + '-setup.log'), timeout=600)
            require(output.strip().endswith('SETUP_OK'), 'Setup remoto incompleto')
        owned.extend(('a', 'b'))  # incluir también setup parcial en limpieza
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(setup, owned))
        for name, phase in [('a', 'seed'), ('b', 'read-b-write'), ('a', 'read-a')]:
            output = run(region, values['compute'][name]['instance_id'], f'{folder}/venv/bin/python {folder}/client.py {folder} {phase}', LOG / (name + '-' + phase + '.log'), timeout=180)
            phases.append(parse_result(output, phase))
            print('PASS: datos ' + phase + ' en EC2 ' + name + ' con LabRole/TLS SQL', flush=True)
    finally:
        if 'a' in owned:
            try:
                script = f'test ! -x {folder}/venv/bin/python || test ! -f {folder}/connection.json || {{ test "$(cat {folder}/owner)" = {run_id} && {folder}/venv/bin/python {folder}/client.py {folder} cleanup; }}'
                output = run(region, values['compute']['a']['instance_id'], script, LOG / 'data-cleanup.log', timeout=180)
                if output.strip():
                    phases.append(parse_result(output, 'cleanup'))
            except Exception:
                errors.append('No se pudieron comprobar sondas SQL/Redis/Dynamo/SQS; revisar logs privados')
        for name in owned:
            try:
                script = f'test ! -d {folder} || {{ test "$(cat {folder}/owner)" = {run_id} && rm -rf -- {folder}; }}; test ! -e {folder}'
                run(region, values['compute'][name]['instance_id'], script, LOG / (name + '-local-cleanup.log'), timeout=90)
            except Exception:
                errors.append('Material remoto no retirado en ' + name)
        connection_file.unlink(missing_ok=True)
        try:
            if upload_attempted:
                remove_config_versions(region, bucket, key, account, version)
        except Exception:
            errors.append('No se pudo retirar versión privada de configuración en S3')
        require(not errors, '; '.join(errors))
    summary['status'] = 'PASS'
    summary['cleanup'] = 'probe-data, remote-private-files, local-connection-file and exact S3 object version removed'
    private_write(LOG / 'report.json', json.dumps(summary, indent=2) + '\n')
    print('PASS: datos compartidos A/B, sondas y material privado retirados', flush=True)


if __name__ == '__main__':
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        main()
    except KeyboardInterrupt:
        print('Interrumpido; revisar limpieza T06 antes de destruir infra.', file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        safe_error = str(exc) if isinstance(exc, (AccessError, SSMError)) else type(exc).__name__
        if LOG.is_dir():
            private_write(LOG / 'report.json', json.dumps({'status': 'FAIL', 'error': safe_error}))
        print('FALLA T06: ' + safe_error + '; diagnóstico en .local/t06, sin imprimir credenciales.', file=sys.stderr)
        sys.exit(1)
