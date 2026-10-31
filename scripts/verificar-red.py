#!/usr/bin/env python3
"""T02: valida red desplegada y controles S3 mediante APIs de solo lectura."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / "config/entorno.json").read_text())

    def aws(service, operation, *params):
        return json.loads(subprocess.check_output(["aws", "--region", config["region"], "--no-cli-pager", service, operation, *params, "--output", "json"], text=True, timeout=90))

    network = json.loads(subprocess.check_output(["terraform", "-chdir=" + str(ROOT / "terraform/infra"), "output", "-json", "network"], text=True))
    subnet_ids = [zone["id"] for kind in ("public_subnets", "private_subnets", "db_subnets") for zone in network[kind].values()]
    subnets = aws("ec2", "describe-subnets", "--subnet-ids", *subnet_ids)["Subnets"]
    assert len(subnets) == 6, "Faltan subredes"
    for key, zone in config["zones"].items():
        for output, cidr_key in (("public_subnets", "public_cidr"), ("private_subnets", "private_cidr"), ("db_subnets", "db_cidr")):
            subnet = next(s for s in subnets if s["SubnetId"] == network[output][key]["id"])
            assert subnet["CidrBlock"] == zone[cidr_key] and subnet["AvailabilityZone"] == zone["availability_zone"]
            if output != "public_subnets":
                assert subnet["MapPublicIpOnLaunch"] is False
    print("PASS: seis subredes, CIDR/AZ y privadas sin IP pública automática")
    nats = aws("ec2", "describe-nat-gateways", "--filter", "Name=vpc-id,Values=" + network["vpc_id"])["NatGateways"]
    nats = [n for n in nats if n["State"] == "available"]
    assert len(nats) == 2
    for key, private in network["private_subnets"].items():
        route = aws("ec2", "describe-route-tables", "--route-table-ids", private["route_table_id"])["RouteTables"][0]
        default = next(r for r in route["Routes"] if r.get("DestinationCidrBlock") == "0.0.0.0/0")
        nat = next(n for n in nats if n["NatGatewayId"] == default["NatGatewayId"])
        assert nat["SubnetId"] == network["public_subnets"][key]["id"]
        assert any(a["SubnetId"] == private["id"] for a in route["Associations"])
    db_route = aws("ec2", "describe-route-tables", "--route-table-ids", network["db_route_table_id"])["RouteTables"][0]
    assert all(r.get("GatewayId") == "local" for r in db_route["Routes"])
    assert {a.get("SubnetId") for a in db_route["Associations"]} == {s["id"] for s in network["db_subnets"].values()}
    print("PASS: NAT propio por AZ y datos solo con ruta local")
    ids = list(network["gateway_endpoint_ids"].values()) + [network["sqs_endpoint_id"]]
    endpoints = aws("ec2", "describe-vpc-endpoints", "--vpc-endpoint-ids", *ids)["VpcEndpoints"]
    assert len(endpoints) == 3 and all(e["State"] == "available" for e in endpoints)
    for endpoint in endpoints:
        if endpoint["VpcEndpointType"] == "Gateway":
            assert set(endpoint["RouteTableIds"]) == {p["route_table_id"] for p in network["private_subnets"].values()}
        else:
            assert endpoint["PrivateDnsEnabled"]
            assert set(endpoint["SubnetIds"]) == {p["id"] for p in network["private_subnets"].values()}
    print("PASS: S3/DynamoDB por rutas privadas y SQS Interface con DNS privado")
    for group, port, source in (("application_security_group_id", 8080, network["alb_security_group_id"]), ("endpoint_security_group_id", 443, network["application_security_group_id"])):
        rules = aws("ec2", "describe-security-group-rules", "--filters", "Name=group-id,Values=" + network[group])["SecurityGroupRules"]
        incoming = [r for r in rules if not r["IsEgress"]]
        assert len(incoming) == 1
        rule = incoming[0]
        assert rule["IpProtocol"] == "tcp" and rule["FromPort"] == rule["ToPort"] == port
        assert rule.get("ReferencedGroupInfo", {}).get("GroupId") == source
        assert not rule.get("CidrIpv4") and not rule.get("CidrIpv6")
    print("PASS: SG EC2 y SQS admiten únicamente su SG de origen y puerto")
    assert aws("s3api", "get-bucket-versioning", "--bucket", args.bucket)["Status"] == "Enabled"
    encryption = aws("s3api", "get-bucket-encryption", "--bucket", args.bucket)["ServerSideEncryptionConfiguration"]
    assert encryption["Rules"][0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"
    assert all(aws("s3api", "get-public-access-block", "--bucket", args.bucket)["PublicAccessBlockConfiguration"].values())
    policy = json.loads(aws("s3api", "get-bucket-policy", "--bucket", args.bucket)["Policy"])
    assert any(s["Effect"] == "Deny" and s.get("Condition", {}).get("Bool", {}).get("aws:SecureTransport") == "false" for s in policy["Statement"])
    print("PASS: bucket privado, cifrado, versionado y transporte HTTPS requerido")


if __name__ == "__main__":
    main()
