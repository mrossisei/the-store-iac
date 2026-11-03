#!/usr/bin/env python3
"""Publica corrección de contrato con tags nuevos, preservando todo T07 inmutable."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publisher', ROOT / 'scripts/publicar-imagenes.py')
pub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pub)


def main():
    folder = ROOT / '.local/t08'
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    partial = folder / 'releases-application.partial.json'
    target = ROOT / 'terraform/imagenes/releases-aplicacion.json'
    original = json.loads(pub.MANIFEST.read_text())
    source = ROOT / 'the-store/src/checkout/src/checkout/orders/HttpOrdersService.ts'
    source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    repo = pub.repositories()['checkout']
    settings = pub.aws('ecr', 'describe-repositories', '--repository-names', repo.split('/', 1)[1])['repositories'][0]
    if settings['imageTagMutability'] != 'IMMUTABLE':
        raise ValueError('No publicar sin inmutabilidad')
    previous = json.loads(target.read_text()) if target.exists() else json.loads(partial.read_text()) if partial.exists() else {}
    # Conservar otras correcciones ya publicadas (p. ej. Orders).
    new = copy.deepcopy(previous or original)
    new['derived_from'] = 'releases.json'
    base = original['versions']['v1']['checkout']['repository'] + '@' + original['versions']['v1']['checkout']['digest']
    with pub.docker_login(repo.split('/')[0]) as env:
        for version in ('v1', 'v2'):
            tag = version + '-t08'
            remote = pub.description(repo, tag)
            if remote:
                recorded = previous.get('versions', {}).get(version, {}).get('checkout', {})
                if recorded.get('tag') != tag or recorded.get('digest') != remote['imageDigest'] or recorded.get('source_sha256') != source_sha:
                    raise ValueError('Tag de corrección existente sin registro verificable; no reescribir')
                new['versions'][version]['checkout'] = recorded
            else:
                logfile = folder / ('checkout-' + tag + '-build-push.log')
                with logfile.open('w') as log:
                    logfile.chmod(0o600)
                    pub.command(['docker', 'buildx', 'build', '--platform', 'linux/amd64', '--provenance=false', '--load',
                                 '--build-arg', 'BASE_IMAGE=' + base, '--build-arg', 'STORE_VERSION=' + version,
                                 '--tag', repo + ':' + tag, '-f', str(ROOT / 'the-store/src/checkout/Dockerfile.t08'),
                                 str(ROOT / 'the-store/src/checkout')], env=env, log=log)
                    pub.command(['docker', 'push', repo + ':' + tag], env=env, log=log)
                digest = pub.description(repo, tag)['imageDigest']
                new['versions'][version]['checkout'] = {
                    'repository': repo, 'digest': digest, 'tag': tag, 'platform': 'linux/amd64',
                    'source_revision': pub.command(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).strip(),
                    'source_tree_dirty': bool(pub.command(['git', '-C', str(ROOT), 'status', '--porcelain']).strip()),
                    'source_sha256': source_sha, 'base_image': base,
                }
            pub.save(partial, new)
            partial.chmod(0o600)
            print('PASS: Checkout ' + tag + ' publicado y registrado sin modificar tags originales.', flush=True)
        repos = pub.repositories()
        for version in ('v1', 'v2'):
            pub.validate(new, version, repos)
        pub.save(target, new)
    print('PASS: manifest de aplicación completo; T07 original intacto.', flush=True)


if __name__ == '__main__':
    main()
