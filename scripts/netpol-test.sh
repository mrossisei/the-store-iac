#!/usr/bin/env bash
# Verifica que las NetworkPolicies del entorno permitan sólo los flujos
# declarados. Usa curl desde los pods reales (ui, catalog) y desde un pod
# "intruso" creado ad hoc en el namespace.
# Uso: scripts/netpol-test.sh the-store-prod
set -uo pipefail
NS="${1:?uso: $0 <namespace>}"
PASS=0; FAILN=0
result() { if [ "$1" = "$2" ]; then printf "  \033[32m✔\033[0m %s\n" "$3"; PASS=$((PASS+1)); else printf "  \033[31m✘\033[0m %s (esperado: %s, obtenido: %s)\n" "$3" "$2" "$1"; FAILN=$((FAILN+1)); fi; }

# Devuelve "open" si el puerto acepta conexión TCP y "blocked" si hay timeout.
probe_from_deploy() { # deploy host port
  local rc
  kubectl -n "$NS" exec "deploy/$1" -- curl -s -o /dev/null -m 4 "http://$2:$3/" >/dev/null 2>&1; rc=$?
  case $rc in 28|7) echo blocked ;; *) echo open ;; esac
}
probe_from_intruder() { # host port
  local rc
  kubectl -n "$NS" exec intruder -- sh -c "nc -z -w 4 $1 $2" >/dev/null 2>&1; rc=$?
  [ $rc -eq 0 ] && echo open || echo blocked
}

echo "NetworkPolicies en $NS:"
kubectl -n "$NS" get networkpolicies -o name | sed 's/^/  /'
policies=$(kubectl -n "$NS" get networkpolicies -o name | wc -l)
persist=$(kubectl -n "$NS" get statefulset catalog-db >/dev/null 2>&1 && echo yes || echo no)

echo; echo "Pod intruso (busybox) en el namespace..."
kubectl -n "$NS" delete pod intruder --ignore-not-found --wait=true >/dev/null 2>&1
kubectl -n "$NS" run intruder --image=busybox:1.37 --restart=Never --command -- sleep 3600 >/dev/null
kubectl -n "$NS" wait --for=condition=Ready pod/intruder --timeout=120s >/dev/null

echo; echo "Flujos permitidos por la aplicación:"
result "$(probe_from_deploy ui catalog 80)"   open "ui -> catalog:80"
result "$(probe_from_deploy ui carts 80)"     open "ui -> carts:80"
result "$(probe_from_deploy ui orders 80)"    open "ui -> orders:80"
result "$(probe_from_deploy ui checkout 80)"  open "ui -> checkout:80"
result "$(probe_from_deploy checkout orders 80)" open "checkout -> orders:80"
if [ "$persist" = yes ]; then
  result "$(probe_from_deploy catalog catalog-db 3306)" open "catalog -> catalog-db:3306"
  result "$(probe_from_deploy orders orders-db 5432)"   open "orders -> orders-db:5432"
  result "$(probe_from_deploy orders orders-mq 5672)"   open "orders -> orders-mq:5672"
fi

echo; echo "Flujos que deben estar bloqueados:"
if [ "$policies" -gt 0 ]; then expect=blocked; else expect=open; echo "  (sin NetworkPolicies: se espera que todo esté abierto)"; fi
result "$(probe_from_intruder catalog 80)"  "$expect" "intruso -> catalog:80"
result "$(probe_from_intruder ui 8080)"     "$expect" "intruso -> ui:8080"
result "$(probe_from_deploy catalog orders 80)" "$expect" "catalog -> orders:80 (no declarado)"
if [ "$persist" = yes ]; then
  result "$(probe_from_deploy ui catalog-db 3306)"     "$expect" "ui -> catalog-db:3306 (no declarado)"
  result "$(probe_from_intruder orders-db 5432)"       "$expect" "intruso -> orders-db:5432"
  result "$(probe_from_intruder checkout-redis 6379)"  "$expect" "intruso -> checkout-redis:6379"
fi

kubectl -n "$NS" delete pod intruder --wait=false >/dev/null 2>&1
echo; echo "Resultado: $PASS OK, $FAILN fallidos"
[ "$FAILN" -eq 0 ]
