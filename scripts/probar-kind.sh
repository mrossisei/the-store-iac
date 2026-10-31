#!/usr/bin/env bash
# Prueba local aislada: kind/Calico, entrada NodePort y enforcement de policies.
# No toca el kubeconfig global ni otros clusters; siempre elimina su cluster.
set -euo pipefail
for setting in max_user_instances max_user_watches; do
  minimum=1024
  [ "$setting" = max_user_watches ] && minimum=524288
  current=$(cat "/proc/sys/fs/inotify/$setting")
  if [ "$current" -lt "$minimum" ]; then
    echo "Requisito del host: fs.inotify.$setting >= $minimum (actual: $current)." >&2
    echo 'Ajustarlo con un administrador antes de repetir la prueba.' >&2
    exit 1
  fi
done
if ! docker image save --help | grep -q -- --platform; then
  echo 'Se requiere Docker con image save --platform (API 1.48 o posterior).' >&2
  exit 1
fi
ROOT=$(cd "$(dirname "$0")/.." && pwd)
PROBE_DIR=$(mktemp -d)
CLUSTER="t01-probe-$$"
CREATED=false
cleanup() {
  local result=$?
  if $CREATED && [ "$result" -ne 0 ]; then
    mkdir -p "$ROOT/.local"
    kind export logs "$ROOT/.local/$CLUSTER-logs" --name "$CLUSTER" >/dev/null 2>&1 || true
  fi
  if $CREATED; then kind delete cluster --name "$CLUSTER" >/dev/null 2>&1; fi
  rm -rf "$PROBE_DIR"
}
trap cleanup EXIT
export KUBECONFIG="$PROBE_DIR/kubeconfig"
export ROOT PROBE_DIR
python3 - <<'PY'
import json, os, socket
from pathlib import Path
root=Path(os.environ['ROOT']); out=Path(os.environ['PROBE_DIR'])
cfg=json.loads((root/'config/entorno.json').read_text()); tools=json.loads((root/'config/herramientas.json').read_text())
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
(out/'port').write_text(str(port))
kind={'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4',
 'networking':{'disableDefaultCNI':True,'podSubnet':cfg['kind']['pod_cidr'],'serviceSubnet':cfg['kind']['service_cidr'],'apiServerAddress':'127.0.0.1'},
 'nodes':[{'role':'control-plane','extraPortMappings':[{'containerPort':cfg['kind']['ui_node_port'],'hostPort':port,'listenAddress':'127.0.0.1'}]},{'role':'worker'}]}
(out/'kind.json').write_text(json.dumps(kind))
(out/'image').write_text(tools['kind_node_image'])
(out/'calico-url').write_text(tools['calico_manifest_url'])
PY
CREATED=true
# Con CNI deshabilitado los nodos no estarán Ready hasta instalar Calico.
kind create cluster --name "$CLUSTER" --config "$PROBE_DIR/kind.json" --image "$(cat "$PROBE_DIR/image")"
curl -fLsS --retry 2 --connect-timeout 10 --max-time 120 "$(cat "$PROBE_DIR/calico-url")" -o "$PROBE_DIR/calico.yaml"
# El pool de Calico debe coincidir con el CIDR configurado en kind.
sed -i 's#192.168.0.0/16#10.244.0.0/16#g' "$PROBE_DIR/calico.yaml"
sed -i 's/# - name: CALICO_IPV4POOL_CIDR/- name: CALICO_IPV4POOL_CIDR/; s/#   value: "10.244.0.0\/16"/  value: "10.244.0.0\/16"/' "$PROBE_DIR/calico.yaml"
# Mismo publicador oficial; evitar repetir pulls lentos de Quay por cada nodo.
sed -i 's#quay.io/calico/#docker.io/calico/#g' "$PROBE_DIR/calico.yaml"
for image in $(sed -n 's/^[[:space:]]*image: \(docker.io\/calico\/.*\)$/\1/p' "$PROBE_DIR/calico.yaml" | sort -u); do
  docker pull --platform=linux/amd64 "$image"
  # Docker con image store containerd puede conservar un índice multi-arquitectura
  # incompleto. Exportar solo amd64 evita content digest not found al importar.
  docker image save --platform=linux/amd64 "$image" -o "$PROBE_DIR/image.tar"
  kind load image-archive "$PROBE_DIR/image.tar" --name "$CLUSTER"
done
kubectl apply --server-side -f "$PROBE_DIR/calico.yaml" >/dev/null
kubectl rollout status -n kube-system daemonset/calico-node --timeout=600s
kubectl wait --for=condition=Ready nodes --all --timeout=180s
kubectl run server --image=busybox:1.37.0 --labels=app=server --restart=Never --command -- sh -c 'mkdir -p /www; echo alive >/www/index.html; exec httpd -f -p 8080 -h /www'
kubectl run allowed --image=busybox:1.37.0 --labels=access=yes --restart=Never --command -- sleep 600
kubectl run denied --image=busybox:1.37.0 --labels=access=no --restart=Never --command -- sleep 600
kubectl wait --for=condition=Ready pods --all --timeout=180s
POD_IP=$(kubectl get pod server -o jsonpath='{.status.podIP}')
for pod in allowed denied; do
  kubectl exec "$pod" -- wget -q -T 5 -O - "http://$POD_IP:8080" | grep -qx alive
done
cat <<'YAML' | kubectl apply -f - >/dev/null
apiVersion: v1
kind: Service
metadata:
  name: ui-probe
spec:
  type: NodePort
  selector: {app: server}
  ports:
    - {port: 80, targetPort: 8080, nodePort: 30080}
YAML
curl --retry 10 --retry-all-errors --retry-delay 1 --retry-max-time 30 -fsS "http://127.0.0.1:$(cat "$PROBE_DIR/port")" | grep -qx alive
cat <<'YAML' | kubectl apply -f - >/dev/null
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: probe
spec:
  podSelector: {matchLabels: {app: server}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {access: 'yes'}}
      ports:
        - {protocol: TCP, port: 8080}
YAML
BLOCKED=false
for attempt in 1 2 3 4 5; do
  kubectl exec allowed -- wget -q -T 5 -O - "http://$POD_IP:8080" | grep -qx alive
  if ! kubectl exec denied -- wget -q -T 3 -O - "http://$POD_IP:8080" >/dev/null 2>&1; then BLOCKED=true; break; fi
  sleep 1
done
$BLOCKED || { echo 'FALLA: Calico no bloqueó el origen sin permiso' >&2; exit 1; }
kubectl delete networkpolicy probe >/dev/null
kubectl exec denied -- wget -q -T 5 -O - "http://$POD_IP:8080" | grep -qx alive
echo 'PASS: dos nodos Ready, mapeo NodePort, tráfico permitido/bloqueado y recuperación.'
