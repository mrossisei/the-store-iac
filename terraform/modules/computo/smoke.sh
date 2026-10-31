#!/usr/bin/env bash
# Prueba sobre el kind real del host, antes de desplegar app (NodePort libre).
set -Eeuo pipefail
export PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export KUBECONFIG=/var/lib/the-store/kubeconfig
NS="t03-probe-$(cat /proc/sys/kernel/random/uuid | cut -c1-8)"
cleanup() {
  code=$?
  trap - EXIT
  kubectl delete namespace "$NS" --ignore-not-found --wait=true --timeout=60s >/dev/null || code=1
  exit "$code"
}
trap cleanup EXIT
kubectl create namespace "$NS" >/dev/null
kubectl -n "$NS" run server --image=busybox:1.37.0 --labels=app=server --restart=Never --command -- sh -c 'mkdir -p /www; echo alive >/www/index.html; exec httpd -f -p 8080 -h /www'
for client in allowed denied; do
  kubectl -n "$NS" run "$client" --image=busybox:1.37.0 --labels="access=$client" --restart=Never --command -- sleep 300
done
kubectl -n "$NS" wait --for=condition=Ready pods --all --timeout=180s
IP=$(kubectl -n "$NS" get pod server -o jsonpath='{.status.podIP}')
for client in allowed denied; do kubectl -n "$NS" exec "$client" -- wget -q -T 5 -O - "http://$IP:8080" | grep -qx alive; done
NODE_PORT=$(jq -r .environment.kind.ui_node_port /opt/the-store/config.json)
HOST_PORT=$(jq -r .environment.kind.host_ui_port /opt/the-store/config.json)
cat <<YAML | kubectl apply -n "$NS" -f - >/dev/null
apiVersion: v1
kind: Service
metadata:
  name: ui-probe
spec:
  type: NodePort
  selector: {app: server}
  ports: [{port: 80, targetPort: 8080, nodePort: $NODE_PORT}]
YAML
curl -fsS --retry 12 --retry-all-errors --retry-delay 1 --retry-max-time 40 "http://127.0.0.1:$HOST_PORT" | grep -qx alive
for client in allowed denied; do
  kubectl -n "$NS" exec "$client" -- wget -q -T 5 -O - "http://ui-probe.$NS.svc.cluster.local" | grep -qx alive
done
python3 - "$NS" <<'PY_DNS'
import ipaddress,json,re,subprocess,sys
from pathlib import Path
config=json.loads(Path('/opt/the-store/config.json').read_text())['environment']
text=subprocess.check_output(['kubectl','-n',sys.argv[1],'exec','allowed','--','nslookup','sqs.'+config['region']+'.amazonaws.com'],text=True,timeout=20)
addresses=[ipaddress.ip_address(a) for a in re.findall(r'Address(?: [0-9]+)?:\s+([0-9.]+)',text)]
for zone in config['zones'].values():
    assert any(a in ipaddress.ip_network(zone['private_cidr']) for a in addresses), 'SQS no resuelve a un endpoint privado de cada AZ'
print('PASS: DNS de servicio y SQS privado desde el pod')
PY_DNS
cat <<'YAML' | kubectl apply -n "$NS" -f - >/dev/null
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: only-allowed
spec:
  podSelector: {matchLabels: {app: server}}
  policyTypes: [Ingress]
  ingress:
    - from: [{podSelector: {matchLabels: {access: allowed}}}]
      ports: [{protocol: TCP, port: 8080}]
YAML
BLOCKED=false
for attempt in 1 2 3 4 5; do
  kubectl -n "$NS" exec allowed -- wget -q -T 5 -O - "http://$IP:8080" | grep -qx alive
  if output=$(kubectl -n "$NS" exec denied -- wget -T 3 -O - "http://$IP:8080" 2>&1); then
    sleep 1
  elif [[ "$output" == *'timed out'* ]]; then BLOCKED=true; break
  else echo "Sonda inválida: $output" >&2; exit 1; fi
done
$BLOCKED || { echo 'No se probó bloqueo por Calico' >&2; exit 1; }
kubectl -n "$NS" delete networkpolicy only-allowed >/dev/null
kubectl -n "$NS" exec denied -- wget -q -T 5 -O - "http://$IP:8080" | grep -qx alive
echo 'PASS: NodePort/hostPort, clientes positivos, bloqueo y recuperación.'
