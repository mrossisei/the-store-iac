#!/usr/bin/env python3
"""Local Orders regression: POST -> PostgreSQL -> GET, including process restart.

Usage: python3 scripts/probar-orders-postgres.py --image the-store/t08-orders-fixed:v1
Requires Docker and a locally available postgres:17-alpine. No cloud access.
Use --logs .local/t08-orders/v1 to retain requests, SQL rows and container logs.
"""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import uuid


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def request(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        return json.load(response)


def wait_for(action, description):
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            return action()
        except (subprocess.CalledProcessError, urllib.error.URLError, TimeoutError,
                ConnectionError):
            time.sleep(1)
    raise RuntimeError(f"Timed out waiting for {description}")


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--postgres-image", default="postgres:17-alpine")
    parser.add_argument("--logs", type=Path, default=Path(".local/t08-orders/regression"))
    args = parser.parse_args()
    args.logs.mkdir(mode=0o700, parents=True, exist_ok=True)
    args.logs.chmod(0o700)
    suffix = uuid.uuid4().hex[:10]
    pg, app, network = (f"t08-orders-{suffix}-{part}" for part in ("pg", "app", "net"))
    created = []
    items = [
        {"productId": "6d1e1e46-14e5-4b38-a72a-cc1a58d39566", "quantity": 1,
         "unitCost": 100, "totalCost": 100},
        {"productId": "a125b6cf-806e-4166-b34c-45baf1d772cf", "quantity": 3,
         "unitCost": 245, "totalCost": 735},
    ]
    payload = {"items": items, "shippingAddress": {
        "firstName": "Local", "lastName": "Regression", "email": "local@example.test",
        "address1": "Test 123", "address2": "", "city": "Test",
        "zipCode": "1000", "state": "BA",
    }}
    evidence = {"image": args.image, "request": payload}
    (args.logs / "request.json").write_text(json.dumps(payload, indent=2) + "\n")

    def sql(query):
        return docker("exec", pg, "psql", "-U", "orders", "-d", "orders", "-At", "-c", query)

    def check_items(actual, context):
        assert len(actual) == 2, f"{context}: expected two products, got {actual}"
        assert sorted(actual, key=lambda item: item["productId"]) == sorted(
            items, key=lambda item: item["productId"]
        ), f"{context}: UUID/quantity/price mismatch: {actual}"
        for item in actual:
            uuid.UUID(item["productId"])

    try:
        docker("network", "create", network)
        docker("run", "-d", "--pull=never", "--name", pg, "--network", network,
               "-e", "POSTGRES_USER=orders", "-e", "POSTGRES_PASSWORD=local-regression",
               "-e", "POSTGRES_DB=orders", args.postgres_image)
        created.append(pg)
        wait_for(lambda: sql("SELECT 1"), "PostgreSQL")
        docker("run", "-d", "--pull=never", "--name", app, "--network", network,
               "-p", "127.0.0.1::8080",
               "-e", "RETAIL_ORDERS_PERSISTENCE_PROVIDER=postgres",
               "-e", f"RETAIL_ORDERS_PERSISTENCE_ENDPOINT={pg}:5432",
               "-e", "RETAIL_ORDERS_PERSISTENCE_NAME=orders",
               "-e", "RETAIL_ORDERS_PERSISTENCE_USERNAME=orders",
               "-e", "RETAIL_ORDERS_PERSISTENCE_PASSWORD=local-regression",
               "-e", "RETAIL_ORDERS_MESSAGING_PROVIDER=in-memory", args.image)
        created.append(app)
        port = docker("port", app, "8080/tcp").rsplit(":", 1)[1]
        url = f"http://127.0.0.1:{port}/orders"
        wait_for(lambda: request(url), "Orders API")
        evidence["post"] = request(url, payload)
        evidence["get"] = request(url)
        evidence["sql"] = json.loads(sql(
            "SELECT coalesce(json_agg(json_build_object('productId', product_id, "
            "'quantity', quantity, 'unitCost', unit_cost, 'totalCost', total_cost)), '[]') "
            "FROM order_items"
        ))
        assert len(evidence["get"]) == 1, evidence["get"]
        # Capture both views before asserting, including when the old mapping fails.
        (args.logs / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        check_items(evidence["sql"], "PostgreSQL rows")
        check_items(evidence["post"]["items"], "POST response")
        check_items(evidence["get"][0]["items"], "GET response")
        docker("restart", app)
        # Docker can allocate a new ephemeral published port on restart.
        port = docker("port", app, "8080/tcp").rsplit(":", 1)[1]
        url = f"http://127.0.0.1:{port}/orders"
        evidence["after_restart"] = wait_for(lambda: request(url), "Orders restart")
        assert len(evidence["after_restart"]) == 1, evidence["after_restart"]
        assert evidence["after_restart"][0]["id"] == evidence["post"]["id"]
        check_items(evidence["after_restart"][0]["items"], "GET after restart")
        evidence["result"] = "PASS"
        print(f"PASS: {args.image}: two UUIDs and all quantities/costs survive PostgreSQL and restart")
    finally:
        (args.logs / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
        for container in reversed(created):
            (args.logs / f"{container.rsplit('-', 1)[1]}.log").write_text(
                subprocess.run(["docker", "logs", container], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
            )
            docker("rm", "-fv", container)
        subprocess.run(["docker", "network", "rm", network], check=True, stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
