#!/usr/bin/env python3
"""Crea/verifica el bucket del bootstrap sin consultar S3 Object Lock (SCP Academy)."""
import json
import os
import re
import subprocess


def main():
    bucket = os.environ["TF_STATE_BUCKET"]
    region = os.environ["TF_STATE_REGION"]
    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket):
        raise ValueError("Nombre de bucket inválido")
    base = ["aws", "--region", region, "--no-cli-pager"]

    def call(*args):
        return subprocess.run(base + list(args), capture_output=True, text=True, timeout=90)

    identity = call("sts", "get-caller-identity", "--output", "json")
    if identity.returncode:
        raise RuntimeError("No se pudo autenticar la sesión AWS")
    account = json.loads(identity.stdout)["Account"]
    head = call("s3api", "head-bucket", "--bucket", bucket, "--expected-bucket-owner", account)
    if head.returncode:
        if "(404)" not in head.stderr and "NoSuchBucket" not in head.stderr:
            raise RuntimeError("El bucket existe o no se puede comprobar su propietario; no se modifica")
        arguments = ["s3api", "create-bucket", "--bucket", bucket]
        if region != "us-east-1":
            arguments += ["--create-bucket-configuration", "LocationConstraint=" + region]
        created = call(*arguments)
        if created.returncode:
            raise RuntimeError("AWS rechazó la creación del bucket")
        tags = call("s3api", "put-bucket-tagging", "--bucket", bucket, "--tagging", json.dumps({"TagSet": [{"Key": "Project", "Value": "the-store"}, {"Key": "ManagedBy", "Value": "terraform"}]}))
        if tags.returncode:
            raise RuntimeError("Bucket creado, pero falló su etiquetado; revisar antes de continuar")
    else:
        tags = call("s3api", "get-bucket-tagging", "--bucket", bucket, "--expected-bucket-owner", account, "--output", "json")
        if tags.returncode:
            raise RuntimeError("No se adopta un bucket preexistente sin etiquetas verificables")
        actual = {t["Key"]: t["Value"] for t in json.loads(tags.stdout)["TagSet"]}
        if actual.get("Project") != "the-store" or actual.get("ManagedBy") != "terraform":
            raise RuntimeError("El bucket pertenece a otro uso; no se adopta")
    print("Bucket propio del proyecto disponible; Terraform aplica sus controles dedicados")


if __name__ == "__main__":
    main()
