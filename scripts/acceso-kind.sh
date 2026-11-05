#!/usr/bin/env bash
# Terraform corre este script en cada plan y apply.
#
# La API de kind solo escucha dentro de cada EC2 privada. Para cada clúster espera
# que kind esté listo, trae su kubeconfig y abre un túnel SSM a un puerto local.
# Devuelve a Terraform las rutas de los kubeconfigs. Stdout debe ser solo ese JSON.
set -euo pipefail

# Proceso separado del provider: conserva tráfico por el túnel mientras Terraform
# compila/sube imágenes o espera por RDS. No cambia los timeouts de AWS.
if [ "${1:-}" = --mantener ]; then
  archivo=$2 pid=$3 lock=$4
  inicio=$(cat "/proc/$pid/stat" 2>/dev/null) || exit 0
  inicio=${inicio##*) }
  inicio=$(awk '{print $20}' <<< "$inicio")
  exec 9>"$lock"
  flock -w 35 9 || exit 0
  while kill -0 "$pid" 2>/dev/null; do
    actual=$(cat "/proc/$pid/stat" 2>/dev/null) || break
    actual=${actual##*) }
    [ "$(awk '{print $20}' <<< "$actual")" = "$inicio" ] || break
    [ "${actual%% *}" != Z ] || break
    kubectl --kubeconfig "$archivo" --request-timeout=5s get --raw /readyz >/dev/null 2>&1 || true
    sleep 30
  done
  exit 0
fi

region=$1
script="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
dir="$(dirname "$(dirname "$script")")/.local"
mkdir -p -m 700 "$dir"

listo() {
  kubectl --kubeconfig "$1" --request-timeout=5s get --raw /readyz >/dev/null 2>&1
}

mantener_tunel() {
  local puerto=$1 archivo=$2 pid
  [ -f "$dir/tunel-$puerto.pid" ] || return 1
  pid=$(cat "$dir/tunel-$puerto.pid")
  kill -0 "$pid" 2>/dev/null || return 1
  setsid bash "$script" --mantener "$archivo" "$pid" "$dir/tunel-$puerto.keepalive.lock" \
    >"$dir/tunel-$puerto.keepalive.log" 2>&1 </dev/null &
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
  local instancia=$1 puerto=$2 archivo=$3 pid args grupo
  if [ -f "$dir/tunel-$puerto.pid" ]; then
    pid=$(cat "$dir/tunel-$puerto.pid")
    if [[ "$pid" =~ ^[0-9]+$ ]] && [ "$pid" -gt 1 ]; then
      args=$(ps -p "$pid" -o args= 2>/dev/null || true)
      # El PID puede haberse reutilizado. Solo detenemos nuestro túnel SSM.
      if [[ "$args" == *"ssm start-session"* && "$args" == *"localPortNumber"*"$puerto"* ]]; then
        grupo=$(ps -p "$pid" -o pgid= | tr -d ' ')
        if [ "$grupo" = "$pid" ]; then
          kill -- "-$pid" 2>/dev/null || true
        else
          kill "$pid" 2>/dev/null || true
        fi
      fi
    fi
  fi
  setsid aws ssm start-session --region "$region" --target "$instancia" \
    --document-name AWS-StartPortForwardingSession \
    --parameters "{\"portNumber\":[\"6443\"],\"localPortNumber\":[\"$puerto\"]}" \
    >"$dir/tunel-$puerto.log" 2>&1 </dev/null &
  echo $! > "$dir/tunel-$puerto.pid"
  for _ in $(seq 30); do
    if listo "$archivo"; then
      mantener_tunel "$puerto" "$archivo"
      return 0
    fi
    sleep 2
  done
  echo "No se pudo abrir el túnel a $instancia" >&2
  exit 1
}

conectar() {
  local instancia=$1 puerto=$2 archivo="$dir/kind-$3.kubeconfig"
  local identidad="$archivo.instance-id"
  # Un puerto abierto puede apuntar al clúster de una EC2 anterior.
  if [ -f "$archivo" ] && [ -f "$identidad" ] &&
    [ "$(cat "$identidad")" = "$instancia" ] && listo "$archivo" &&
    mantener_tunel "$puerto" "$archivo"; then
    return 0
  fi
  traer_kubeconfig "$instancia" "$puerto" "$archivo"
  abrir_tunel "$instancia" "$puerto" "$archivo"
  printf '%s\n' "$instancia" > "$identidad"
}

conectar "$2" 16443 a
conectar "$3" 26443 b
printf '{"kubeconfig_a":"%s","kubeconfig_b":"%s"}\n' "$dir/kind-a.kubeconfig" "$dir/kind-b.kubeconfig"
