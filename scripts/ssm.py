"""Run Command con plazo y validación por invocación; no muestra stderr de AWS."""
import json
import os
from pathlib import Path
import re
import subprocess
import time


class SSMError(RuntimeError):
    pass


def aws(region, service, operation, *args):
    result = subprocess.run(['aws', '--region', region, '--no-cli-pager', '--cli-connect-timeout', '10', '--cli-read-timeout', '20', service, operation, *args, '--output', 'json'], capture_output=True, text=True, timeout=90,
                            env=dict(os.environ, AWS_PAGER='', AWS_EC2_METADATA_DISABLED='true'))
    if result.returncode:
        error = re.search(r'\(([A-Za-z0-9_.-]+)\) when calling', result.stderr)
        raise SSMError(error.group(1) if error else 'AWSCommandFailed')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def run(region, instance, script, log, timeout=2400):
    command = aws(region, 'ssm', 'send-command', '--instance-ids', instance, '--document-name', 'AWS-RunShellScript', '--parameters', json.dumps({'commands': [script], 'executionTimeout': [str(timeout)]}), '--timeout-seconds', '120')['Command']['CommandId']
    deadline = time.monotonic() + timeout + 120
    finished = False
    try:
        while time.monotonic() < deadline:
            try:
                result = aws(region, 'ssm', 'get-command-invocation', '--command-id', command, '--instance-id', instance)
            except SSMError as exc:
                if str(exc) != 'InvocationDoesNotExist':
                    raise
                time.sleep(3)
                continue
            if result['Status'] in ('Pending', 'InProgress', 'Delayed'):
                time.sleep(5)
                continue
            finished = True
            log = Path(log)
            log.parent.mkdir(exist_ok=True, parents=True, mode=0o700)
            log.write_text(result.get('StandardOutputContent', '') + '\n' + result.get('StandardErrorContent', ''))
            log.chmod(0o600)
            if result['Status'] != 'Success' or result.get('ResponseCode') != 0:
                raise SSMError('Invocación ' + result['Status'] + '; diagnóstico en ' + str(log))
            return result.get('StandardOutputContent', '')
        raise SSMError('Tiempo límite de Run Command')
    except BaseException:
        if not finished:
            try:
                aws(region, 'ssm', 'cancel-command', '--command-id', command, '--instance-ids', instance)
            except Exception:
                pass
        raise
