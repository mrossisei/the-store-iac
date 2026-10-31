#!/usr/bin/env bash
# Root, host dedicado AL2023. Nunca borra un clúster existente para repararlo.
set -Eeuo pipefail
umask 077
[ "$EUID" -eq 0 ] || { echo 'Se requiere root' >&2; exit 1; }
exec 9>/run/the-store-prepare.lock
flock -n 9 || { echo 'Ya hay una preparación en curso' >&2; exit 1; }
BASE=/var/lib/the-store
mkdir -p "$BASE"
rm -f "$BASE/status.json"
trap 'code=$?; if [ "$code" -ne 0 ]; then echo "FAIL código=$code" > "$BASE/bootstrap-error"; fi' EXIT
export PATH=/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export KUBECONFIG="$BASE/kubeconfig"
export AWS_EC2_METADATA_DISABLED=false
setting() { python3 -c 'import json,sys; v=json.load(open("/opt/the-store/config.json"));
for k in sys.argv[1].split("."): v=v[k]
print(v)' "$1"; }
CLUSTER=$(python3 -c 'import json; c=json.load(open("/opt/the-store/config.json")); print(c["environment"]["zones"][c["zone"]]["cluster_name"])')
KIND_VERSION=$(setting tools.kind_version)
KUBE_VERSION=$(setting tools.kubernetes_version)
NODE_IMAGE=$(setting tools.kind_node_image)

# El repositorio AL2023 queda en el snapshot de la AMI fijada, sin releasever=latest.
if ! command -v docker >/dev/null || ! command -v jq >/dev/null; then
  dnf install -y docker jq conntrack-tools socat iptables
fi
if ! command -v aws >/dev/null; then dnf install -y awscli-2; fi
systemctl enable --now amazon-ssm-agent
cat > /etc/sysctl.d/90-the-store-kind.conf <<'EOF'
fs.inotify.max_user_instances=1024
fs.inotify.max_user_watches=524288
net.ipv4.ip_forward=1
EOF
sysctl -p /etc/sysctl.d/90-the-store-kind.conf
modprobe br_netfilter
modprobe overlay
systemctl enable --now docker

fetch() {
  curl -fLsS --retry 3 --retry-all-errors --connect-timeout 15 --max-time 180 "$1" -o "$2"
}
if ! command -v kind >/dev/null || ! kind version | grep -Fq "v$KIND_VERSION "; then
  fetch "https://github.com/kubernetes-sigs/kind/releases/download/v$KIND_VERSION/kind-linux-amd64" "$BASE/kind.download"
  echo "$(setting tools.kind_binary_sha256)  $BASE/kind.download" | sha256sum -c -
  install -m 0755 "$BASE/kind.download" /usr/local/bin/kind
  rm "$BASE/kind.download"
fi
if ! command -v kubectl >/dev/null || [ "$(kubectl version --client -o json | jq -r .clientVersion.gitVersion)" != "v$KUBE_VERSION" ]; then
  fetch "https://dl.k8s.io/release/v$KUBE_VERSION/bin/linux/amd64/kubectl" "$BASE/kubectl.download"
  echo "$(setting tools.kubectl_sha256)  $BASE/kubectl.download" | sha256sum -c -
  install -m 0755 "$BASE/kubectl.download" /usr/local/bin/kubectl
  rm "$BASE/kubectl.download"
fi

python3 - <<'PY'
import json
from pathlib import Path
config=json.loads(Path('/opt/the-store/config.json').read_text()); env=config['environment']; k=env['kind']
kind={'kind':'Cluster','apiVersion':'kind.x-k8s.io/v1alpha4',
      'networking':{'disableDefaultCNI':True,'apiServerAddress':k['api_address'],'apiServerPort':k['api_port'],'podSubnet':k['pod_cidr'],'serviceSubnet':k['service_cidr']},
      'nodes':[{'role':'control-plane','extraPortMappings':[{'containerPort':k['ui_node_port'],'hostPort':k['host_ui_port'],'listenAddress':'0.0.0.0'}]},{'role':'worker'}]}
Path('/var/lib/the-store/kind.json').write_text(json.dumps(kind))
PY
DESIRED=$(cat "$BASE/kind.json"; echo "$NODE_IMAGE")
CONFIG_SHA=$(printf '%s' "$DESIRED" | sha256sum | cut -d' ' -f1)
if kind get clusters 2>/dev/null | grep -Fxq "$CLUSTER"; then
  [ -f "$BASE/cluster-config.sha256" ] && [ "$(cat "$BASE/cluster-config.sha256")" = "$CONFIG_SHA" ] || {
    echo 'Configuración del clúster existente diferente/desconocida; revisar reemplazo con Terraform.' >&2; exit 1;
  }
  mapfile -t NODES < <(docker ps -aq --filter "label=io.x-k8s.kind.cluster=$CLUSTER")
  [ "${#NODES[@]}" -eq 2 ] || { echo 'Clúster incompleto; se conservan contenedores para diagnóstico.' >&2; exit 1; }
  docker start "${NODES[@]}" >/dev/null
else
  kind create cluster --name "$CLUSTER" --config "$BASE/kind.json" --image "$NODE_IMAGE" --retain
  echo "$CONFIG_SHA" > "$BASE/cluster-config.sha256"
fi
kind export kubeconfig --name "$CLUSTER" --kubeconfig "$KUBECONFIG"
chmod 600 "$KUBECONFIG"
mapfile -t NODES < <(docker ps -aq --filter "label=io.x-k8s.kind.cluster=$CLUSTER")
docker update --restart=always "${NODES[@]}" >/dev/null

if [ ! -f "$BASE/calico.yaml" ]; then
  fetch "$(setting tools.calico_manifest_url)" "$BASE/calico.download"
  echo "$(setting tools.calico_manifest_sha256)  $BASE/calico.download" | sha256sum -c -
  python3 - <<'PY'
import json
from pathlib import Path
k=json.loads(Path('/opt/the-store/config.json').read_text())['environment']['kind']
s=Path('/var/lib/the-store/calico.download').read_text().replace('quay.io/calico/', 'docker.io/calico/')
s=s.replace('# - name: CALICO_IPV4POOL_CIDR', '- name: CALICO_IPV4POOL_CIDR').replace('#   value: "192.168.0.0/16"', '  value: "'+k['pod_cidr']+'"')
Path('/var/lib/the-store/calico.yaml').write_text(s)
PY
fi
if [ ! -f "$BASE/calico-loaded" ]; then
  for image in $(sed -n 's/^[[:space:]]*image: \(docker.io\/calico\/.*\)$/\1/p' "$BASE/calico.yaml" | sort -u); do
    docker image inspect "$image" >/dev/null 2>&1 || docker pull --platform=linux/amd64 "$image"
    if docker image save --help | grep -q -- --platform; then
      docker image save --platform=linux/amd64 "$image" -o "$BASE/image.tar"
    else
      docker image save "$image" -o "$BASE/image.tar"
    fi
    kind load image-archive "$BASE/image.tar" --name "$CLUSTER"
  done
  rm -f "$BASE/image.tar" "$BASE/calico.download"
  touch "$BASE/calico-loaded"
fi
kubectl apply --server-side -f "$BASE/calico.yaml" >/dev/null
kubectl rollout status -n kube-system daemonset/calico-node --timeout=600s
kubectl rollout status -n kube-system deployment/calico-kube-controllers --timeout=180s
kubectl wait --for=condition=Ready nodes --all --timeout=180s
kubectl rollout status -n kube-system deployment/coredns --timeout=180s
[ "$(kubectl get nodes -o json | jq '.items|length')" -eq 2 ]
UID_CLUSTER=$(kubectl get namespace kube-system -o json | jq -r .metadata.uid)
jq -n --arg cluster "$CLUSTER" --arg uid "$UID_CLUSTER" --arg config "$CONFIG_SHA" \
  --arg docker "$(docker --version)" --arg kind "$(kind version)" \
  '{status:"PASS",cluster:$cluster,cluster_uid:$uid,config_sha:$config,docker:$docker,kind:$kind}' > "$BASE/status.json"
rm -f "$BASE/bootstrap-error"
echo 'PASS: kind de dos nodos y Calico preparados; configuración conservada.'
