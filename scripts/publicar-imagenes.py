#!/usr/bin/env python3
"""Publica versiones inmutables; select sólo valida ECR y emite referencias por digest."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'config/entorno.json').read_text())
SERVICES = CONFIG['services']
REGION = CONFIG['region']
MANIFEST = ROOT / 'terraform/imagenes/releases.json'


def command(args, *, env=None, stdin=None, log=None, timeout=7200):
    result = subprocess.run(args, input=stdin, text=True, env=env, stdout=log or subprocess.PIPE,
                            stderr=log or subprocess.PIPE, timeout=timeout)
    if result.returncode:
        # Never echo process stderr: authentication failures can contain credentials.
        raise RuntimeError(f'{args[0]} {args[1]} falló ({result.returncode}); revisar log privado si existe')
    return result.stdout


def aws(service, operation, *args):
    return json.loads(command(['aws', '--region', REGION, '--no-cli-pager', service, operation,
                               *args, '--output', 'json'], timeout=90) or '{}')


def repositories():
    result = command(['terraform', f'-chdir={ROOT / "terraform/imagenes"}', 'output', '-json', 'repositories'])
    repos = json.loads(result)
    if set(repos) != set(SERVICES):
        raise ValueError('Se requieren exactamente los cinco repositorios del contrato')
    for service, repo in repos.items():
        if not re.fullmatch(r'\d{12}\.dkr\.ecr\.' + re.escape(REGION) + r'\.amazonaws\.com/' + CONFIG['project'] + '/' + service, repo):
            raise ValueError('Repositorio inesperado')
    return repos


def description(repo, version):
    images = aws('ecr', 'describe-images', '--repository-name', repo.split('/', 1)[1])['imageDetails']
    return next((image for image in images if version in image.get('imageTags', [])), None)


def validate(manifest, version, repos):
    if manifest.get('schema') != 1 or manifest.get('region') != REGION:
        raise ValueError('Schema/región inválidos')
    images = manifest.get('versions', {}).get(version, {})
    if set(images) != set(SERVICES):
        raise ValueError('Publicación incompleta')
    for service, item in images.items():
        tag = item.get('tag', version)
        if (item.get('repository') != repos[service] or item.get('platform') != 'linux/amd64'
                or not re.fullmatch(r'sha256:[a-f0-9]{64}', item.get('digest', ''))
                or not isinstance(tag, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', tag)):
            raise ValueError('Referencia inválida: ' + service)
        remote = description(repos[service], tag)
        if remote is None or remote['imageDigest'] != item['digest']:
            raise ValueError('Digest incorrecto en ECR: ' + service)
    return {service: item['repository'] + '@' + item['digest'] for service, item in images.items()}


def save(path, manifest):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as temp:
        json.dump(manifest, temp, indent=2, sort_keys=True)
        temp.write('\n')
    os.replace(temp.name, path)


@contextmanager
def docker_login(registry):
    # Do not inherit credentials helpers or write to ~/.docker/config.json.
    with tempfile.TemporaryDirectory(prefix='t07-docker-') as directory:
        env = dict(os.environ, DOCKER_CONFIG=directory)
        password = command(['aws', '--region', REGION, 'ecr', 'get-login-password'], timeout=90)
        command(['docker', 'login', '--username', 'AWS', '--password-stdin', registry], env=env, stdin=password)
        del password
        yield env


def publish(path, version, resume=False, jobs=2):
    if jobs not in (1, 2):
        raise ValueError('Máximo dos builds simultáneos')
    repos = repositories()
    manifest = json.loads(path.read_text()) if path.exists() else {'schema': 1, 'region': REGION, 'versions': {}}
    if manifest.get('schema') != 1 or manifest.get('region') != REGION:
        raise ValueError('Manifest inválido')
    previous = manifest['versions'].get(version, {})
    if previous and not resume:
        raise ValueError('Versión ya publicada o parcial; usar --resume sólo para completar faltantes')
    missing = []
    for service, repo in repos.items():
        remote_repo = aws('ecr', 'describe-repositories', '--repository-names', repo.split('/', 1)[1])['repositories'][0]
        if remote_repo['imageTagMutability'] != 'IMMUTABLE':
            raise ValueError('Repositorio sin inmutabilidad: ' + service)
        image = description(repo, version)
        if image:
            item = previous.get(service, {})
            if not resume or item.get('digest') != image['imageDigest'] or item.get('repository') != repo or item.get('platform') != 'linux/amd64':
                raise ValueError('Reescritura o tag preexistente sin registro verificable: ' + service)
        elif service in previous:
            raise ValueError('Manifest registra un tag ausente: ' + service)
        else:
            missing.append(service)
    lock = threading.Lock()
    logdir = ROOT / '.local/t07'
    logdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with docker_login(next(iter(repos.values())).split('/')[0]) as env:
        def build(service):
            repo = repos[service]
            logfile = logdir / f'{version}-{service}.log'
            with logfile.open('w') as log:
                logfile.chmod(0o600)
                command(['docker', 'buildx', 'build', '--platform', 'linux/amd64', '--provenance=false', '--load',
                         '--build-arg', 'STORE_VERSION=' + version, '--tag', repo + ':' + version,
                         str(ROOT / 'the-store/src' / SERVICES[service])], env=env, log=log)
                inspect = json.loads(command(['docker', 'image', 'inspect', repo + ':' + version], env=env))[0]
                if inspect['Os'] != 'linux' or inspect['Architecture'] != 'amd64':
                    raise ValueError('Arquitectura incorrecta')
                command(['docker', 'push', repo + ':' + version], env=env, log=log)
            digest = description(repo, version)['imageDigest']
            with lock:
                manifest['versions'].setdefault(version, {})[service] = {
                    'repository': repo, 'digest': digest, 'platform': 'linux/amd64',
                    'source_revision': command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).strip(),
                    'source_tree_dirty': bool(command(['git', '-C', str(ROOT), 'status', '--porcelain']).strip())}
                save(path, manifest)
            print(f'{version}/{service}: {digest}', flush=True)
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            list(pool.map(build, missing))
    validate(manifest, version, repos)


def restore(path, version):
    """Recupera tags perdidos del Lab desde copias locales verificadas; sin builds."""
    repos = repositories()
    manifest = json.loads(path.read_text())
    if manifest.get('schema') != 1 or manifest.get('region') != REGION:
        raise ValueError('Manifest inválido')
    images = manifest.get('versions', {}).get(version, {})
    if set(images) != set(SERVICES):
        raise ValueError('Publicación incompleta')
    missing = []
    for service, repo in repos.items():
        item = images[service]
        tag = item.get('tag', version)
        if item.get('repository') != repo or item.get('platform') != 'linux/amd64' or not re.fullmatch(r'sha256:[a-f0-9]{64}', item.get('digest', '')):
            raise ValueError('Referencia inválida: ' + service)
        if not isinstance(tag, str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}', tag):
            raise ValueError('Tag inválido')
        settings = aws('ecr', 'describe-repositories', '--repository-names', repo.split('/', 1)[1])['repositories'][0]
        if settings['imageTagMutability'] != 'IMMUTABLE':
            raise ValueError('Repositorio sin inmutabilidad')
        remote = description(repo, tag)
        if remote:
            if remote['imageDigest'] != item['digest']:
                raise ValueError('Tag remoto diferente; no sobrescribir')
            continue
        info = json.loads(command(['docker', 'image', 'inspect', repo + ':' + tag]))[0]
        if repo + '@' + item['digest'] not in info.get('RepoDigests', []):
            raise ValueError('Copia local diferente del digest registrado')
        missing.append((service, tag))
    if missing:
        with docker_login(next(iter(repos.values())).split('/')[0]) as env:
            folder = ROOT / '.local/t07'
            folder.mkdir(parents=True, exist_ok=True, mode=0o700)
            for service, tag in missing:
                path_log = folder / ('restore-' + version + '-' + service + '.log')
                with path_log.open('w') as log:
                    path_log.chmod(0o600)
                    command(['docker', 'push', repos[service] + ':' + tag], env=env, log=log)
                if description(repos[service], tag)['imageDigest'] != images[service]['digest']:
                    raise ValueError('Push no conservó digest; no editar manifest')
    validate(manifest, version, repos)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['publish', 'select', 'restore'])
    parser.add_argument('version', choices=['v1', 'v2'])
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--jobs', type=int, choices=[1, 2], default=2)
    args = parser.parse_args()
    try:
        if args.command in ('publish', 'restore'):
            # OS lock automatically releases on errors; no stale lock flag.
            (ROOT / '.local').mkdir(exist_ok=True, mode=0o700)
            with (ROOT / '.local/t07-publish.lock').open('w') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                if args.command == 'publish':
                    publish(args.manifest, args.version, args.resume, args.jobs)
                else:
                    restore(args.manifest, args.version)
        else:
            images = validate(json.loads(args.manifest.read_text()), args.version, repositories())
            print(json.dumps({'app_version': args.version, 'images': images}, indent=2, sort_keys=True))
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
