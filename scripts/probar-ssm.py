#!/usr/bin/env python3
"""T01: sonda temporal EC2/PassRole/SSM; elimina únicamente sus recursos propios."""
import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create-probe", action="store_true", required=True,
                        help="crea una EC2 temporal facturable en una subred pública default; sin ingreso SG")
    parser.parse_args()
    if not shutil.which("session-manager-plugin"):
        raise SystemExit("Instalar session-manager-plugin antes de crear la sonda")
    config = json.loads((ROOT / "config/entorno.json").read_text())
    tools = json.loads((ROOT / "config/herramientas.json").read_text())
    env = dict(os.environ, AWS_PAGER="", AWS_EC2_METADATA_DISABLED="true")
    base = ["aws", "--region", config["region"], "--no-cli-pager", "--cli-connect-timeout", "10", "--cli-read-timeout", "20"]

    def aws(service, operation, *args, timeout=90):
        result = subprocess.run(base + [service, operation, *args, "--output", "json"],
                                capture_output=True, text=True, timeout=timeout, env=env)
        if result.returncode:
            error_file = folder / "aws-error.txt"
            error_file.write_text(result.stderr)
            error_file.chmod(0o600)
            raise subprocess.CalledProcessError(result.returncode, ["aws", service, operation])
        return json.loads(result.stdout) if result.stdout.strip() else {}

    run_id = "t01-ssm-" + uuid.uuid4().hex[:12]
    tags = [{"Key": "Project", "Value": config["project"]}, {"Key": "Probe", "Value": run_id}]
    folder = ROOT / ".local" / run_id
    folder.mkdir(parents=True, mode=0o700)
    record = folder / "resources.json"
    owned = {}

    def remember(key, value):
        owned[key] = value
        record.write_text(json.dumps(owned, indent=2) + "\n")
        record.chmod(0o600)

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupted)
    tunnel = None
    try:
        vpcs = aws("ec2", "describe-vpcs", "--filters", "Name=is-default,Values=true")["Vpcs"]
        if len(vpcs) != 1:
            raise RuntimeError("Esta sonda requiere una VPC default existente; no crea ni altera una")
        vpc = vpcs[0]["VpcId"]
        subnets = aws("ec2", "describe-subnets", "--filters", "Name=vpc-id,Values=" + vpc,
                      "Name=availability-zone,Values=" + config["zones"]["a"]["availability_zone"])["Subnets"]
        if not subnets:
            raise RuntimeError("No existe una subred default en la AZ elegida")
        ami = aws("ssm", "get-parameter", "--name", "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64")["Parameter"]["Value"]
        remember("ami", ami)
        sg = aws("ec2", "create-security-group", "--group-name", run_id,
                 "--description", "Temporary T01 SSM probe - no inbound rules", "--vpc-id", vpc,
                 "--tag-specifications", json.dumps([{"ResourceType": "security-group", "Tags": tags}]))["GroupId"]
        remember("security_group", sg)
        # Se conserva solo salida HTTPS para el agente; no se abre SSH ni otro ingreso.
        aws("ec2", "revoke-security-group-egress", "--group-id", sg, "--ip-permissions",
            json.dumps([{"IpProtocol": "-1", "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]))
        aws("ec2", "authorize-security-group-egress", "--group-id", sg, "--ip-permissions",
            json.dumps([{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]))
        instance = aws("ec2", "run-instances", "--image-id", ami, "--instance-type", tools["instance_type_candidate"],
                       "--count", "1", "--client-token", run_id,
                       "--iam-instance-profile", "Name=" + config["iam"]["instance_profile_name"],
                       "--metadata-options", "HttpTokens=required,HttpPutResponseHopLimit=1",
                       "--network-interfaces", json.dumps([{"DeviceIndex": 0, "SubnetId": subnets[0]["SubnetId"], "Groups": [sg], "AssociatePublicIpAddress": True}]),
                       "--tag-specifications", json.dumps([{"ResourceType": kind, "Tags": tags} for kind in ("instance", "volume")]))["Instances"][0]["InstanceId"]
        remember("instance", instance)
        print("PASS: EC2 t3.large creada con LabInstanceProfile (PassRole efectivo)", flush=True)
        deadline = time.monotonic() + 420
        while time.monotonic() < deadline:
            info = aws("ssm", "describe-instance-information", "--filters", "Key=InstanceIds,Values=" + instance)["InstanceInformationList"]
            if any(i["PingStatus"] == "Online" for i in info):
                break
            time.sleep(5)
        else:
            raise RuntimeError("El agente SSM no se registró Online dentro de 7 minutos")
        print("PASS: agente SSM Online", flush=True)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        with (folder / "session.log").open("w") as log:
            tunnel = subprocess.Popen(base + ["ssm", "start-session", "--target", instance,
                                       "--document-name", "AWS-StartPortForwardingSession", "--parameters",
                                       json.dumps({"portNumber": ["22"], "localPortNumber": [str(port)]})],
                                      stdout=log, stderr=log, env=env, start_new_session=True)
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if tunnel.poll() is not None:
                    raise RuntimeError("La sesión SSM terminó antes de abrir el túnel; consultar el log local")
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=3) as connection:
                        connection.settimeout(5)
                        if connection.recv(256).startswith(b"SSH-"):
                            print("PASS: sesión SSM real y túnel autenticado; banner SSH sin ingreso SG", flush=True)
                            break
                except (OSError, TimeoutError):
                    pass
                time.sleep(2)
            else:
                raise RuntimeError("El túnel no entregó el banner remoto dentro de 90 segundos")
    finally:
        if tunnel is not None and tunnel.poll() is None:
            os.killpg(tunnel.pid, signal.SIGTERM)
            try:
                tunnel.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(tunnel.pid, signal.SIGKILL)
                tunnel.wait()
        # IDs retornados por esta ejecución; jamás búsqueda/borrado global por tags.
        if "instance" in owned:
            aws("ec2", "terminate-instances", "--instance-ids", owned["instance"])
            aws("ec2", "wait", "instance-terminated", "--instance-ids", owned["instance"], timeout=420)
            print("PASS: instancia de prueba terminada", flush=True)
        if "security_group" in owned:
            for attempt in range(24):
                try:
                    aws("ec2", "delete-security-group", "--group-id", owned["security_group"])
                    print("PASS: SG de prueba eliminado", flush=True)
                    break
                except subprocess.CalledProcessError:
                    if attempt == 23:
                        raise
                    time.sleep(5)


if __name__ == "__main__":
    main()
