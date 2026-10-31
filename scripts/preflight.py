#!/usr/bin/env python3
"""T01: comprobaciones locales y consultas AWS de solo lectura; nunca crea recursos."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


def validate_contract(config):
    vpc = ipaddress.ip_network(config["vpc_cidr"])
    networks = []
    if set(config["zones"]) != {"a", "b"}:
        raise ValueError("Se requieren exactamente los clústeres a y b")
    ports = []
    azs = []
    for zone in config["zones"].values():
        azs.append(zone["availability_zone"])
        ports.append(zone["local_api_port"])
        for key in ("public_cidr", "private_cidr", "db_cidr"):
            net = ipaddress.ip_network(zone[key])
            if net.prefixlen != 24 or not net.subnet_of(vpc):
                raise ValueError("Cada subred AWS debe ser /24 y pertenecer a la VPC")
            networks.append(net)
    if len(set(azs)) != 2 or len(set(ports)) != 2:
        raise ValueError("AZ y puertos de acceso deben ser diferentes")
    if any(a.overlaps(b) for i, a in enumerate(networks) for b in networks[i + 1:]):
        raise ValueError("Las subredes AWS se superponen")
    internal = [ipaddress.ip_network(config["kind"][key]) for key in ("pod_cidr", "service_cidr")]
    if internal[0].overlaps(internal[1]) or any(n.overlaps(vpc) for n in internal):
        raise ValueError("Redes kind y VPC deben ser disjuntas")
    if len(set(config["state_keys"].values())) != 3:
        raise ValueError("Las tres raíces deben tener estados diferentes")
    if not 30000 <= config["kind"]["ui_node_port"] <= 32767:
        raise ValueError("NodePort fuera del rango estándar")


def run(command):
    env = dict(os.environ, AWS_EC2_METADATA_DISABLED="true", AWS_PAGER="")
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=40, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, type(exc).__name__
    if result.returncode:
        # No publicar stdout/stderr, ARNs personales, tokens ni archivos de credenciales.
        match = re.search(r"\((\w+)\) when calling", result.stderr)
        return None, match.group(1) if match else "CommandFailed"
    try:
        return json.loads(result.stdout), None
    except json.JSONDecodeError:
        return result.stdout.strip(), None


def collect(offline=False, profile=None, instance_id=None):
    config = json.loads((ROOT / "config/entorno.json").read_text())
    tools = json.loads((ROOT / "config/herramientas.json").read_text())
    results = []

    def record(name, status, detail):
        results.append({"check": name, "status": status, "detail": detail})

    try:
        validate_contract(config)
        record("contrato", "PASS", "CIDR, zonas, puertos y claves de estado coherentes")
    except (ValueError, KeyError) as exc:
        record("contrato", "FAIL", str(exc))
    for tool in ("terraform", "aws", "docker", "kind", "kubectl", "jq", "session-manager-plugin"):
        record("herramienta:" + tool, "PASS" if shutil.which(tool) else "FAIL", "disponible" if shutil.which(tool) else "no instalada")
    docker, error = run(["docker", "info", "--format", "{{json .}}"])
    record("docker", "FAIL" if error else "PASS", error or "daemon accesible")
    if isinstance(docker, dict):
        enough = docker.get("MemTotal", 0) >= 8 * 1024**3
        record("memoria-local", "PASS" if enough else "FAIL", "se requieren al menos 8 GiB para probar kind localmente")

    base = ["aws", "--region", config["region"], "--no-cli-pager", "--cli-connect-timeout", "10", "--cli-read-timeout", "20"]
    if profile:
        base += ["--profile", profile]

    def aws(name, args, predicate=lambda value: True):
        value, error = run(base + args + ["--output", "json"])
        if error:
            record(name, "PENDING", error)
            return None
        try:
            valid = predicate(value)
        except (KeyError, TypeError, IndexError):
            valid = False
        record(name, "PASS" if valid else "FAIL", "consulta verificada" if valid else "la respuesta no cumple el contrato")
        return value

    if offline:
        record("aws", "PENDING", "omitido explícitamente con --offline")
    elif aws("aws:sesion", ["sts", "get-caller-identity"]):
        aws("aws:perfil", ["iam", "get-instance-profile", "--instance-profile-name", config["iam"]["instance_profile_name"]], lambda v: any(r["RoleName"] == config["iam"]["role_name"] for r in v["InstanceProfile"]["Roles"]))
        aws("aws:zonas", ["ec2", "describe-availability-zones", "--zone-names"] + [z["availability_zone"] for z in config["zones"].values()], lambda v: len(v["AvailabilityZones"]) == 2 and all(z["State"] == "available" for z in v["AvailabilityZones"]))
        aws("aws:capacidad", ["ec2", "describe-instance-types", "--instance-types", tools["instance_type_candidate"]], lambda v: v["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"] >= tools["minimum_instance_memory_mib"] and "x86_64" in v["InstanceTypes"][0]["ProcessorInfo"]["SupportedArchitectures"] and v["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"] >= tools["minimum_instance_vcpus"])
        aws("aws:cuota-cpu", ["service-quotas", "get-service-quota", "--service-code", "ec2", "--quota-code", "L-1216C47A"], lambda v: v["Quota"]["Value"] >= 4)
        for engine in ("mysql", "postgres"):
            aws("aws:rds:" + engine, ["rds", "describe-orderable-db-instance-options", "--engine", engine, "--db-instance-class", tools["rds_class_candidate"], "--max-items", "100", "--page-size", "100"], lambda v: any(o.get("MultiAZCapable") and o.get("StorageType") == "gp2" for o in v["OrderableDBInstanceOptions"]))
        aws("aws:redis", ["elasticache", "describe-cache-engine-versions", "--engine", "redis", "--engine-version", tools["redis_engine_version"]], lambda v: bool(v["CacheEngineVersions"]))
        if instance_id:
            aws("aws:ssm-agente", ["ssm", "describe-instance-information", "--filters", "Key=InstanceIds,Values=" + instance_id], lambda v: any(i["PingStatus"] == "Online" for i in v["InstanceInformationList"]))
        else:
            record("aws:ssm-agente", "PENDING", "no se indicó --instance-id; scripts/probar-ssm.py comprueba una sonda temporal")
        record("aws:permisos-escritura", "PENDING", "este script es de solo lectura; PassRole se prueba con probar-ssm.py y cada servicio con su apply")
        record("aws:presupuesto", "PENDING", "completar tarifas actuales y saldo de Academy antes del apply")

    local_failed = any(r["status"] == "FAIL" for r in results)
    pending = any(r["status"] == "PENDING" for r in results)
    status = "FAIL" if local_failed else "PENDING_AWS" if pending else "PASS"
    return {"date": datetime.now(timezone.utc).isoformat(), "status": status, "read_only": True, "results": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="solo herramientas/configuración; no certifica AWS")
    parser.add_argument("--profile")
    parser.add_argument("--instance-id", help="EC2 propia para consultar su agente SSM (no crea una instancia)")
    parser.add_argument("--report", type=Path, help="reporte JSON sin credenciales; usar .local/")
    args = parser.parse_args()
    report = collect(args.offline, args.profile, args.instance_id)
    for result in report["results"]:
        print(f'{result["status"]:7} {result["check"]}: {result["detail"]}')
    print("Resultado:", report["status"])
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
        args.report.chmod(0o600)
    return 1 if report["status"] == "FAIL" else 2 if report["status"] != "PASS" else 0


if __name__ == "__main__":
    sys.exit(main())
