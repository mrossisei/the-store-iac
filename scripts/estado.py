#!/usr/bin/env python3
"""Inicializa una raíz kind con backend S3 separado; no aplica ni migra recursos."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def backend_config(bucket, stack):
    config = json.loads((ROOT / "config/entorno.json").read_text())
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("Nombre de bucket inválido")
    if stack not in config["state_keys"]:
        raise ValueError("Raíz desconocida")
    values = {"bucket": bucket, "key": config["state_keys"][stack], "region": config["region"], "encrypt": True, "use_lockfile": True}
    return "\n".join(f"{key} = {json.dumps(value)}" for key, value in values.items()) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init"])
    parser.add_argument("stack", choices=["infra", "imagenes", "aplicacion"])
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args()
    target = ROOT / "terraform" / args.stack
    if not (target / "providers.tf").is_file():
        parser.error("Esta raíz aún no está implementada; no inicializar una carpeta vacía")
    try:
        config = backend_config(args.bucket, args.stack)
    except ValueError as exc:
        parser.error(str(exc))
    destination = ROOT / ".local" / (args.stack + ".backend.hcl")
    destination.parent.mkdir(exist_ok=True, mode=0o700)
    destination.write_text(config)
    destination.chmod(0o600)
    # Sin -reconfigure ni -migrate-state automáticos: si ya existe otro backend,
    # Terraform debe pedir revisar explícitamente el cambio.
    return subprocess.call(["terraform", f"-chdir={target}", "init", "-input=false", f"-backend-config={destination}"])


if __name__ == "__main__":
    raise SystemExit(main())
