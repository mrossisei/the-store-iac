#!/usr/bin/env python3
"""Publica Orders corregido con tags nuevos; conserva T07 y Checkout T08."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publisher', ROOT / 'scripts/publicar-imagenes.py')
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def main():
    folder = ROOT / '.local/t08'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = ROOT / 'terraform/imagenes/releases-aplicacion.json'
    partial = folder / 'releases-orders.partial.json'
    original = json.loads(pub.MANIFEST.read_text())
    previous = json.loads(partial.read_text()) if partial.exists() else json.loads(target.read_text())
    new = copy.deepcopy(previous)
    new['derived_from'] = 'releases.json'
    source = ROOT / 'the-store/src/orders/src/main/java/com/amazon/sample/orders/entities/OrderEntity.java'
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    repo = pub.repositories()['orders']
    settings = pub.aws('ecr', 'describe-repositories', '--repository-names', repo.split('/', 1)[1])['repositories'][0]
    if settings['imageTagMutability'] != 'IMMUTABLE':
        raise ValueError('No publicar sin inmutabilidad')
    base = original['versions']['v1']['orders']['repository'] + '@' + original['versions']['v1']['orders']['digest']
    with pub.docker_login(repo.split('/')[0]) as env:
        for version in ('v1', 'v2'):
            tag = version + '-t08'
            remote = pub.description(repo, tag)
            if remote:
                recorded = previous['versions'][version]['orders']
                if recorded.get('tag') != tag or recorded.get('digest') != remote['imageDigest'] or recorded.get('source_sha256') != source_sha:
                    raise ValueError('Tag Orders existente sin registro verificable; no reescribir')
            else:
                logfile = folder / ('orders-' + tag + '-build-push.log')
                with logfile.open('w') as log:
                    logfile.chmod(0o600)
                    pub.command(['docker', 'buildx', 'build', '--network=host', '--platform', 'linux/amd64', '--provenance=false', '--load',
                                 '--build-arg', 'BASE_IMAGE=' + base, '--build-arg', 'STORE_VERSION=' + version,
                                 '--tag', repo + ':' + tag, '-f', str(ROOT / 'the-store/src/orders/Dockerfile.t08'),
                                 str(ROOT / 'the-store/src/orders')], env=env, log=log)
                    pub.command(['docker', 'push', repo + ':' + tag], env=env, log=log)
                digest = pub.description(repo, tag)['imageDigest']
                new['versions'][version]['orders'] = {
                    'repository': repo, 'digest': digest, 'tag': tag, 'platform': 'linux/amd64',
                    'source_revision': pub.command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).strip(),
                    'source_tree_dirty': bool(pub.command(['git', '-C', str(ROOT), 'status', '--porcelain']).strip()),
                    'source_sha256': source_sha, 'base_image': base,
                }
            pub.save(partial, new)
            partial.chmod(0o600)
            print('PASS: Orders ' + tag + ' publicado y registrado sin modificar tags originales.', flush=True)
        repos = pub.repositories()
        for version in ('v1', 'v2'):
            pub.validate(new, version, repos)
        pub.save(target, new)
    print('PASS: manifest de aplicación con Checkout y Orders corregidos.', flush=True)


if __name__ == '__main__':
    main()
