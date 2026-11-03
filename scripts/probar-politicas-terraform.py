#!/usr/bin/env python3
"""Ejecuta los tests mock de T09 sin requerir que T08 esté integrado."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.umask(0o077)
    local = ROOT / '.local'
    local.mkdir(mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='t09-mocks-', dir=local) as folder:
        path = Path(folder)
        (path / 'tests').mkdir()
        (path / 'main.tf').write_text('terraform {\nrequired_providers {\nkubernetes = { source = "hashicorp/kubernetes", version = "= 3.4.0" }\n}\n}\n')
        relative = os.path.relpath(ROOT / 'terraform/modules/politicas-kind', path)
        tests = (ROOT / 'terraform/aplicacion/tests/politicas.tftest.hcl').read_text()
        (path / 'tests/politicas.tftest.hcl').write_text(tests.replace('../modules/politicas-kind', relative))
        shutil.copy(ROOT / 'terraform/aplicacion/.terraform.lock.hcl', path / '.terraform.lock.hcl')
        subprocess.run(['terraform', '-chdir=' + folder, 'init', '-backend=false', '-input=false'], check=True)
        subprocess.run(['terraform', '-chdir=' + folder, 'test', '-no-color'], check=True)


if __name__ == '__main__':
    main()
