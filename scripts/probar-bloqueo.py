#!/usr/bin/env python3
"""Crea solo su lock condicional, prueba rechazo de plan y retira solo ese lock."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / "config/entorno.json").read_text())
    key = config["state_keys"]["infra"] + ".tflock"
    lock_id = str(uuid.uuid4())
    base = ["aws", "--region", config["region"], "--no-cli-pager", "s3api"]
    with tempfile.TemporaryDirectory() as temporary:
        body = Path(temporary) / "lock.json"
        body.write_text(json.dumps({"ID": lock_id, "Operation": "OperationTypePlan", "Info": "T02 controlled lock probe", "Who": "the-store-test", "Version": "1.16.1", "Created": datetime.now(timezone.utc).isoformat(), "Path": args.bucket + "/" + config["state_keys"]["infra"]}))
        # Si ya había otro lock, la escritura falla y no se ejecuta el finally.
        subprocess.run(base + ["put-object", "--bucket", args.bucket, "--key", key, "--body", str(body), "--if-none-match", "*"], check=True, capture_output=True, timeout=60)
        try:
            result = subprocess.run(["terraform", "-chdir=" + str(ROOT / "terraform/infra"), "plan", "-no-color", "-input=false", "-lock-timeout=0s"], capture_output=True, text=True, timeout=90)
            assert result.returncode != 0 and "Error acquiring the state lock" in result.stderr, "El plan no falló por el bloqueo esperado"
            print("PASS: otro operador no puede planear mientras el estado está bloqueado")
        finally:
            current = Path(temporary) / "current.json"
            subprocess.run(base + ["get-object", "--bucket", args.bucket, "--key", key, str(current)], check=True, capture_output=True, timeout=60)
            if json.loads(current.read_text()).get("ID") != lock_id:
                raise RuntimeError("El lock cambió de propietario; no se elimina")
            subprocess.run(base + ["delete-object", "--bucket", args.bucket, "--key", key], check=True, capture_output=True, timeout=60)
            print("PASS: solo se retiró el lock de esta prueba")


if __name__ == "__main__":
    main()
