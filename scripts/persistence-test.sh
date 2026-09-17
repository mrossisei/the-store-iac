#!/usr/bin/env bash
# Crea una orden vía la API de orders, reinicia el pod de orders y verifica si
# la orden sobrevive: sí con PostgreSQL (prod), no con in-memory (dev).
# Uso: scripts/persistence-test.sh the-store-prod
set -uo pipefail
NS="${1:?uso: $0 <namespace>}"
EMAIL="persistencia-$(date +%s)@itba.edu.ar"
persist=$(kubectl -n "$NS" get statefulset orders-db >/dev/null 2>&1 && echo yes || echo no)

echo "Namespace $NS (persistencia: $persist)"
echo "1) Creando orden para $EMAIL desde el pod de ui..."
kubectl -n "$NS" exec deploy/ui -- curl -s -m 10 -X POST http://orders/orders \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"firstName\":\"Ada\",\"lastName\":\"Lovelace\",\"items\":[{\"productId\":\"d27cf49f-b689-4a75-a249-d373e0330bb5\",\"quantity\":1,\"totalCost\":150,\"unitCost\":150}]}" \
  | head -c 300; echo

echo "2) Reiniciando el pod de orders (kubectl rollout restart)..."
kubectl -n "$NS" rollout restart deploy/orders >/dev/null
kubectl -n "$NS" rollout status deploy/orders --timeout=180s >/dev/null

echo "3) Consultando órdenes:"
found=$(kubectl -n "$NS" exec deploy/ui -- curl -s -m 10 http://orders/orders | grep -c "$EMAIL")
if [ "$persist" = yes ]; then
  [ "$found" -ge 1 ] && echo "   ✔ la orden sobrevivió al reinicio (PostgreSQL)" || { echo "   ✘ la orden se perdió"; exit 1; }
else
  [ "$found" -eq 0 ] && echo "   ✔ la orden se perdió, como se espera con in-memory" || { echo "   ✘ la orden persistió sin base de datos?"; exit 1; }
fi
