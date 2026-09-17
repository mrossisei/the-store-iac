#!/usr/bin/env bash
# Crea una orden vía la API de orders, mata el pod de orders (simula una caída;
# el ReplicaSet lo recrea) y verifica si la orden sobrevive: sí con PostgreSQL
# (prod), no con in-memory (dev). No deja drift: no se modifica el Deployment.
# Uso: scripts/persistence-test.sh the-store-prod
set -uo pipefail
NS="${1:?uso: $0 <namespace>}"
EMAIL="persistencia-$(date +%s)@itba.edu.ar"
persist=$(kubectl -n "$NS" get statefulset orders-db >/dev/null 2>&1 && echo yes || echo no)

echo "Namespace $NS (persistencia: $persist)"
echo "1) Creando orden para $EMAIL desde el pod de ui..."
resp=$(kubectl -n "$NS" exec deploy/ui -- curl -s -m 10 -X POST http://orders/orders \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"firstName\":\"Ada\",\"lastName\":\"Lovelace\",\"items\":[{\"productId\":\"d27cf49f-b689-4a75-a249-d373e0330bb5\",\"quantity\":1,\"totalCost\":150,\"unitCost\":150}]}")
order_id=$(echo "$resp" | grep -oE '"id":"[^"]+"' | head -1 | cut -d'"' -f4)
echo "   respuesta: $(echo "$resp" | head -c 200)"
[ -n "$order_id" ] || { echo "   ✘ no se pudo crear la orden"; exit 1; }
echo "   id de la orden: $order_id"

echo "2) Matando el pod de orders (kubectl delete pod; el ReplicaSet crea uno nuevo)..."
kubectl -n "$NS" delete pod -l app.kubernetes.io/name=orders --wait=true >/dev/null
kubectl -n "$NS" rollout status deploy/orders --timeout=180s >/dev/null

echo "3) Consultando la orden $order_id tras el reinicio:"
found=$(kubectl -n "$NS" exec deploy/ui -- curl -s -m 10 http://orders/orders | grep -c "$order_id")
if [ "$persist" = yes ]; then
  [ "$found" -ge 1 ] && echo "   ✔ la orden sobrevivió al reinicio (PostgreSQL)" || { echo "   ✘ la orden se perdió"; exit 1; }
else
  [ "$found" -eq 0 ] && echo "   ✔ la orden se perdió, como se espera con in-memory" || { echo "   ✘ la orden persistió sin base de datos?"; exit 1; }
fi
