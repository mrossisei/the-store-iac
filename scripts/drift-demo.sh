#!/usr/bin/env bash
# Demo de detección y corrección de drift: alguien modifica la infraestructura
# "a mano" con kubectl y Terraform lo detecta en el plan y lo corrige en el apply.
# Uso: scripts/drift-demo.sh prod
set -euo pipefail
ENV="${1:-dev}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../terraform/3-app" && pwd)"
NS="the-store-$ENV"
VARFILE="../environments/$ENV.tfvars"
cd "$DIR"
terraform workspace select "$ENV" >/dev/null

echo "1) Estado deseado (Terraform): réplicas de catalog"
kubectl -n "$NS" get deploy catalog -o jsonpath='   replicas={.spec.replicas}{"\n"}'

echo; echo "2) Cambio manual fuera de Terraform: kubectl scale deploy/catalog --replicas=3"
kubectl -n "$NS" scale deploy/catalog --replicas=3
kubectl -n "$NS" delete configmap checkout --wait=true >/dev/null && echo "   (además se borró el ConfigMap 'checkout')"
sleep 3

echo; echo "3) terraform plan detecta el drift:"
terraform plan -input=false -var-file="$VARFILE" -no-color 2>&1 | grep -E "^\s*[~+-]|will be|must be|Plan:" | head -20

echo; echo "4) terraform apply vuelve al estado declarado:"
terraform apply -input=false -auto-approve -var-file="$VARFILE" -no-color 2>&1 | grep -E "Modifying|Creating|complete|Apply complete"
kubectl -n "$NS" get deploy catalog -o jsonpath='   replicas={.spec.replicas}{"\n"}'
kubectl -n "$NS" get configmap checkout -o name | sed 's/^/   restaurado: /'
