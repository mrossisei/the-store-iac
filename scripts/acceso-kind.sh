#!/usr/bin/env bash
# Terraform corre este script en cada plan y apply.
#
# La API de kind solo escucha dentro de cada EC2 privada. Para cada clúster espera
# que kind esté listo, trae su kubeconfig y abre un túnel SSM a un puerto local.
# Devuelve a Terraform las rutas de los kubeconfigs. Stdout debe ser solo ese JSON.
set -euo pipefail
region=$1
dir="$(cd "$(dirname "$0")/.." && pwd)/.local"
mkdir -p -m 700 "$dir"

listo() {
  kubectl --kubeconfig "$1" --request-timeout=5s get --raw /readyz >/dev/null 2>&1
}

traer_kubeconfig() {
  local instancia=$1 puerto=$2 archivo=$3 comando
  for _ in $(seq 180); do # hasta 30 minutos: la EC2 puede estar preparando kind
    if comando=$(aws ssm send-command --region "$region" --instance-ids "$instancia" \
        --document-name AWS-RunShellScript \
        --parameters 'commands=["test -f /var/lib/the-store/status.json && cat /var/lib/the-store/kubeconfig"]' \
        --query Command.CommandId --output text 2>/dev/null) &&
      aws ssm wait command-executed --region "$region" --command-id "$comando" --instance-id "$instancia" 2>/dev/null; then
      (umask 077; aws ssm get-command-invocation --region "$region" --command-id "$comando" --instance-id "$instancia" \
        --query StandardOutputContent --output text | sed "s#https://127.0.0.1:6443#https://127.0.0.1:$puerto#" > "$archivo")
      return 0
    fi
    sleep 10
  done
  echo "kind no estuvo listo en $instancia" >&2
  exit 1
}

abrir_tunel() {
  local instancia=$1 puerto=$2 archivo=$3
  [ -f "$dir/tunel-$puerto.pid" ] && kill "$(cat "$dir/tunel-$puerto.pid")" 2>/dev/null || true
  setsid aws ssm start-session --region "$region" --target "$instancia" \
    --document-name AWS-StartPortForwardingSession \
    --parameters "{\"portNumber\":[\"6443\"],\"localPortNumber\":[\"$puerto\"]}" \
    >"$dir/tunel-$puerto.log" 2>&1 </dev/null &
  echo $! > "$dir/tunel-$puerto.pid"
  for _ in $(seq 30); do
    listo "$archivo" && return 0
    sleep 2
  done
  echo "No se pudo abrir el túnel a $instancia" >&2
  exit 1
}

conectar() {
  local instancia=$1 puerto=$2 archivo="$dir/kind-$3.kubeconfig"
  [ -f "$archivo" ] && listo "$archivo" && return 0
  traer_kubeconfig "$instancia" "$puerto" "$archivo"
  abrir_tunel "$instancia" "$puerto" "$archivo"
}

conectar "$2" 16443 a
conectar "$3" 26443 b
printf '{"kubeconfig_a":"%s","kubeconfig_b":"%s"}\n' "$dir/kind-a.kubeconfig" "$dir/kind-b.kubeconfig"
