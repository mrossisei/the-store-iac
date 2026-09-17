#!/usr/bin/env bash
# Verifica los requisitos del host antes de desplegar The Store con Terraform.
set -uo pipefail

ok()   { printf "  \033[32m✔\033[0m %s\n" "$1"; }
warn() { printf "  \033[33m!\033[0m %s\n" "$1"; WARN=$((WARN+1)); }
fail() { printf "  \033[31m✘\033[0m %s\n" "$1"; FAIL=$((FAIL+1)); }
WARN=0; FAIL=0

echo "Requisitos:"

# Docker
if docker info >/dev/null 2>&1; then
  ok "Docker en ejecución ($(docker version --format '{{.Server.Version}}' 2>/dev/null))"
else
  fail "Docker no está corriendo o el usuario no pertenece al grupo docker"
fi

# Terraform >= 1.10
if command -v terraform >/dev/null 2>&1; then
  v=$(terraform version -json 2>/dev/null | jq -r .terraform_version 2>/dev/null || terraform version | head -1 | sed 's/Terraform v//')
  if [ "$(printf '%s\n1.10.0' "$v" | sort -V | head -1)" = "1.10.0" ]; then ok "Terraform $v"; else fail "Terraform $v (se requiere >= 1.10.0)"; fi
else
  fail "terraform no está instalado"
fi

# kubectl (opcional, para demos y scripts)
if command -v kubectl >/dev/null 2>&1; then ok "kubectl $(kubectl version --client -o json 2>/dev/null | jq -r .clientVersion.gitVersion)"; else warn "kubectl no instalado (opcional; lo usan los scripts de demo)"; fi

# Puertos libres (o en uso por nuestro propio clúster/registry)
ours=$(docker ps --format '{{.Names}}' 2>/dev/null | grep -cE '^(the-store-control-plane|kind-registry)$')
for p in 80 443 5001 6443; do
  if ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE "[:.]$p$"; then
    if [ "$ours" -gt 0 ]; then ok "puerto $p en uso por el clúster the-store ya desplegado"; else fail "puerto $p ocupado en el host"; fi
  else ok "puerto $p libre"; fi
done

# Red docker "kind" preexistente
if docker network inspect kind >/dev/null 2>&1; then
  if [ "$ours" -gt 0 ]; then ok "red docker 'kind' creada por este proyecto"; else warn "ya existe una red docker 'kind' ajena (importala con 'terraform import docker_network.kind kind' o borrala)"; fi
else
  ok "no existe una red docker 'kind' previa"
fi

# Disco
avail_gb=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
if [ "${avail_gb:-0}" -ge 15 ]; then ok "espacio libre en /: ${avail_gb} GB"; elif [ "${avail_gb:-0}" -ge 10 ]; then warn "espacio libre en /: ${avail_gb} GB (recomendado >= 15 GB)"; else fail "espacio libre en /: ${avail_gb} GB (se necesitan al menos 10 GB)"; fi

# Memoria
mem_gb=$(free -g | awk '/^Mem/{print $2}')
if [ "${mem_gb:-0}" -ge 12 ]; then ok "memoria: ${mem_gb} GB"; else warn "memoria: ${mem_gb} GB (recomendado >= 12 GB para dev + prod)"; fi

# inotify (kind recomienda subir los límites)
watches=$(sysctl -n fs.inotify.max_user_watches 2>/dev/null || echo 0)
instances=$(sysctl -n fs.inotify.max_user_instances 2>/dev/null || echo 0)
if [ "$watches" -ge 524288 ] && [ "$instances" -ge 512 ]; then
  ok "inotify: max_user_watches=$watches max_user_instances=$instances"
else
  warn "inotify bajo (watches=$watches instances=$instances). Recomendado: sudo sysctl fs.inotify.max_user_watches=524288 fs.inotify.max_user_instances=512"
fi

# Resolución *.localhost
if getent hosts the-store.localhost >/dev/null 2>&1; then ok "*.localhost resuelve a loopback"; else warn "*.localhost no resuelve: agregá '127.0.0.1 the-store.localhost dev.the-store.localhost' a /etc/hosts"; fi

echo
if [ "$FAIL" -gt 0 ]; then echo "Faltan requisitos ($FAIL errores, $WARN avisos)."; exit 1; fi
echo "Todo listo ($WARN avisos)."
