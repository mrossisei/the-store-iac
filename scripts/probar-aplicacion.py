#!/usr/bin/env python3
"""T08 real: replicas/digests, IMDSv2, APIs de datos A/B y URL pública; sin Cypress."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
import uuid

from acceso_kind import ROOT, private_write, require, validate_manifest
from ssm import aws, run
from verificar import Cluster, observe_order_event
import subprocess
CURRENT_REPORT = None


def output(name):
    import subprocess
    return json.loads(subprocess.check_output(['terraform', '-chdir=' + str(ROOT / 'terraform/infra'), 'output', '-json', name], text=True, timeout=90))


def api(cluster, source, method, path, body=None):
    args = ['curl', '-fsS', '--max-time', '30', '-X', method, '-H', 'Content-Type: application/json']
    if body is not None:
        args += ['--data-binary', json.dumps(body)]
    if source == 'checkout':
        # La imagen de Checkout trae Node pero no curl.
        payload = json.dumps({'url': path, 'method': method, 'body': body})
        code = 'const p=' + payload + ';fetch(p.url,{method:p.method,headers:{"Content-Type":"application/json"},body:p.body===null?undefined:JSON.stringify(p.body),signal:AbortSignal.timeout(30000)}).then(async r=>{if(!r.ok){console.error("HTTP "+r.status);process.exitCode=22;return}console.log(await r.text())}).catch(()=>process.exitCode=1)'
        args = ['node', '-e', code]
    else:
        args.append(path)
    command = cluster.base + ['exec', '-n', cluster.namespace, cluster.pod(source), '--', *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode:
        private_write(ROOT / '.local/t08/api-error.log', source + ' ' + method + ' ' + path + '\n' + result.stderr)
    require(result.returncode == 0, 'Llamada API falló; revisar .local/t08/api-error.log')
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    global CURRENT_REPORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--version', choices=['v1', 'v2'], default='v1')
    parser.add_argument('--report', type=Path, default=ROOT / '.local/t08/application-report.json')
    args = parser.parse_args()
    CURRENT_REPORT = args.report
    args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_write(args.report, json.dumps({'status': 'RUNNING'}))
    manifest_path = args.manifest or os.environ.get('THE_STORE_ACCESS_MANIFEST')
    require(manifest_path, 'Usar acceso.py run')
    validate_manifest(manifest_path)
    manifest = json.loads(Path(manifest_path).read_text())
    spec = importlib.util.spec_from_file_location('release', ROOT / 'scripts/seleccionar-release.py')
    release = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(release)
    images = release.select(args.version)
    env = json.loads((ROOT / 'config/entorno.json').read_text())
    replicas = env['replicas_per_cluster']
    clusters = {key: Cluster(entry, 'the-store') for key, entry in manifest['clusters'].items()}
    checks, flows = [], []
    owned = []
    lb = output('load_balancer')
    data = output('data_resources')
    for key, cluster in clusters.items():
        cluster.bootstrap()
        cluster.application(replicas)
        snapshot = cluster.snapshot()
        require(snapshot['images'] == {service: [reference] for service, reference in images.items()}, 'Deployment con digest/versión incorrectos')
        require(all(values and all(v.endswith(images[s]) for v in values) for s, values in snapshot['runtime_images'].items()), 'Runtime no conserva los digests ECR')
        for service in ('carts', 'orders'):
            cluster.credentials(service)
        ui = cluster.get('service', 'ui', '-n', 'the-store')['spec']
        require(ui['type'] == 'NodePort' and ui['ports'][0]['nodePort'] == env['kind']['ui_node_port'], 'UI no expone NodePort acordado')
        require(all(cluster.get('service', s, '-n', 'the-store')['spec']['type'] == 'ClusterIP' for s in images if s != 'ui'), 'Backend expuesto externamente')
        checks += [key + ':10-ready', key + ':runtime-digests', key + ':carts-orders-imdsv2-LabRole', key + ':nodeport-clusterip']
        # Probar el camino host:8080 en cada target sin confiar solo en ALB.
        command = "set -eu\ncurl -fsS --max-time 20 http://127.0.0.1:8080/catalog | python3 -c \"import sys; s=sys.stdin.read(); assert 'The Store · " + args.version + "' in s; print('DIRECT_UI_OK')\""
        result = run(env['region'], manifest['clusters'][key]['instance_id'], command, args.report.parent / ('direct-' + key + '.log'), timeout=90)
        require('DIRECT_UI_OK' in result, 'UI directa falló')
        checks.append(key + ':ui-direct-version')
        print('PASS ' + key + ': pods/digests/LabRole y UI directa.', flush=True)
    # Escribir desde cada copia y leer desde la otra usando solo APIs de app.
    for first, other in (('a', 'b'), ('b', 'a')):
        a, b = clusters[first], clusters[other]
        customer = 't08-' + uuid.uuid4().hex
        product = 'd27cf49f-b689-4a75-a249-d373e0330bb5'
        email = customer + '@example.com'
        owned.append({'customer': customer, 'writer': first, 'reader': other})
        private_write(args.report.parent / 'probe-owned.json', json.dumps(owned, indent=2))
        try:
            products = api(a, 'ui', 'GET', 'http://catalog/catalog/products')
            require(products, 'Catalog/MySQL no devuelve productos')
            api(a, 'ui', 'POST', 'http://carts/carts/' + customer + '/items', {'itemId': product, 'quantity': 1, 'unitPrice': 100})
            items = api(b, 'ui', 'GET', 'http://carts/carts/' + customer + '/items')
            require(any(i['itemId'] == product and i['quantity'] == 1 for i in items), 'Cart/DynamoDB no compartido entre kind')
            request = {'items': [{'id': product, 'name': 'T08 probe', 'quantity': 1, 'price': 100}], 'shippingAddress': {'firstName': 'TP', 'lastName': 'Redes', 'email': email, 'address1': '100 Main Street', 'city': 'Anytown', 'zip': '11111', 'state': 'CA'}}
            api(a, 'ui', 'POST', 'http://checkout/checkout/' + customer + '/update', request)
            checkout = api(b, 'ui', 'GET', 'http://checkout/checkout/' + customer)
            require(checkout['shippingAddress']['email'] == email, 'Checkout/Redis no compartido entre kind')
            # La compra debe atravesar Checkout→Orders, con dirección conservada.
            submitted = api(a, 'ui', 'POST', 'http://checkout/checkout/' + customer + '/submit')
            order_id = submitted['orderId']
            orders = api(b, 'checkout', 'GET', 'http://orders/orders')
            order = next((o for o in orders if o['id'] == order_id), None)
            require(order and order.get('shippingAddress') and order['shippingAddress']['email'] == email, 'Orders/PostgreSQL no conservó dirección/identidad entre kind')
            require(any(item['productId'] == product and item['unitCost'] == 100 and item['quantity'] == 1 and item['totalCost'] == 100 for item in order['items']), 'Orders no conservó producto/precios de Checkout')
            require(observe_order_event({'region': env['region'], 'queue_url': data['sqs_queue_url']}, order_id), 'SDK Orders no produjo evento SQS de la nueva orden')
            flows.append({'writer': first, 'reader': other, 'order_id': order_id, 'sqs_event': True, 'cart_dynamodb': True, 'checkout_redis': True, 'orders_postgres': True})
            print('PASS compra API ' + first + '→' + other + ': carrito, checkout, orden/precios y SQS.', flush=True)
        finally:
            original_error = sys.exc_info()[0] is not None
            cleanup_errors = []
            try:
                api(a, 'ui', 'DELETE', 'http://carts/carts/' + customer)
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__ + ':cart')
            # Checkout no expone DELETE: retirar solo la key privada de esta sonda.
            cleanup = "const r=require('redis').createClient({url:process.env.RETAIL_CHECKOUT_PERSISTENCE_REDIS_URL});(async()=>{await r.connect();await r.del(" + json.dumps(customer) + ");await r.quit();console.log('REMOVED')})().catch(()=>process.exit(1))"
            try:
                a.execute(a.pod('checkout'), 'node', '-e', cleanup)
            except Exception as exc:
                cleanup_errors.append(type(exc).__name__ + ':checkout')
            if cleanup_errors:
                private_write(args.report.parent / 'probe-cleanup-errors.json', json.dumps(cleanup_errors))
                require(original_error, 'No se retiraron todas las sondas de datos; revisar probe-owned.json')
    for _ in range(30):
        targets = aws(env['region'], 'elbv2', 'describe-target-health', '--target-group-arn', lb['target_group_arn'])['TargetHealthDescriptions']
        if len(targets) == 2 and {t['Target']['Id'] for t in targets} == set(lb['target_ids'].values()) and all(t['TargetHealth']['State'] == 'healthy' for t in targets):
            break
        time.sleep(5)
    else:
        raise RuntimeError('ALB no tiene ambos targets healthy')
    url = output('url')
    with urllib.request.urlopen(url + '/catalog', timeout=30) as response:
        require(response.status == 200 and 'The Store · ' + args.version in response.read().decode(), 'ALB no devuelve versión esperada')
    checks += ['alb-both-healthy', 'alb-http-version', 'shared-data-and-sdk-a-b-a']
    private_write(args.report, json.dumps({'status': 'PASS', 'version': args.version, 'checks': checks, 'flows': flows, 'snapshots': {k:c.snapshot() for k,c in clusters.items()}}, indent=2) + '\n')
    print('PASS T08: 20 pods, digests, LabRole, datos/API A↔B, Orders/SQS y ambas UI/ALB.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import traceback
        folder = ROOT / '.local/t08'
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        private_write(folder / 'application-error.log', traceback.format_exc())
        if CURRENT_REPORT is not None:
            private_write(CURRENT_REPORT, json.dumps({'status': 'FAIL', 'error': type(exc).__name__}))
        print('FALLA T08: ' + type(exc).__name__ + '; revisar evidencia privada.', file=sys.stderr)
        sys.exit(1)
