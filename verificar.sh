#!/usr/bin/env bash
# Verifica que el entorno desplegado funcione: la tienda responde, se puede
# completar una compra, la orden persiste y las reglas de segmentacion de red
# permiten solo lo declarado.
#
# Uso: ./verificar.sh
set -uo pipefail
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/the-store.kubeconfig}"
NS=the-store
BASE=http://the-store.localhost
PRODUCTO=d27cf49f-b689-4a75-a249-d373e0330bb5   # "The Quiet Quill", $150
OK=0; FALLA=0
check() { if eval "$2"; then echo "  OK    $1"; OK=$((OK+1)); else echo "  FALLA $1"; FALLA=$((FALLA+1)); fi; }

# Sonda de conectividad desde un microservicio: exit 28 de curl = timeout =
# bloqueado por NetworkPolicy. Los Services de la aplicacion escuchan en el 80.
abierto()   { kubectl exec -n $NS deploy/$1 -- curl -s -m 3 -o /dev/null "http://$2:$3/" >/dev/null 2>&1; [ $? -ne 28 ]; }
bloqueado() { ! abierto "$@"; }

echo "1) Estado del cluster"
check "los 9 pods de la aplicacion estan corriendo" '[ "$(kubectl get pods -n $NS --no-headers | grep -c Running)" -ge 9 ]'
check "los 3 nodos estan Ready"                      '[ "$(kubectl get nodes --no-headers | grep -c " Ready")" -eq 3 ]'

echo "2) La tienda responde"
check "la pagina principal responde 200"  '[ "$(curl -s -o /dev/null -w %{http_code} $BASE/)" = 200 ]'
check "el catalogo lista 6 productos"     '[ "$(curl -s $BASE/catalog | grep -c product-name)" = 6 ]'

echo "3) Compra completa y persistencia"
J=$(mktemp); trap 'rm -f $J' EXIT
curl -s -o /dev/null -b $J -c $J -X POST $BASE/cart --data-urlencode productId=$PRODUCTO --data-urlencode quantity=1
check "el producto entra al carrito" 'curl -s -b $J -c $J $BASE/cart | tr -d "\n" | grep -q "The Quiet Quill"'
curl -s -o /dev/null -b $J -c $J $BASE/checkout
curl -s -o /dev/null -b $J -c $J -X POST $BASE/checkout --data-urlencode firstName=John --data-urlencode lastName=Doe \
  --data-urlencode email=john@example.com --data-urlencode address1="100 Main Street" --data-urlencode city=Anytown \
  --data-urlencode zipCode=11111 --data-urlencode state=CA
curl -s -o /dev/null -b $J -c $J -X POST $BASE/checkout/delivery --data-urlencode token=priority-mail
check "la orden se confirma por \$165" 'curl -s -b $J -c $J -X POST $BASE/checkout/payment --data-urlencode "cardHolder=John Doe" \
  --data-urlencode cardNumber=1234567890123456 --data-urlencode expiryDate=01/35 --data-urlencode cvc=123 | tr -d "\n" | grep -q "\$165"'
check "la orden quedo guardada en PostgreSQL" 'kubectl exec -n $NS deploy/ui -- curl -s -m 5 http://orders/orders | grep -q createdDate'

echo "4) Segmentacion de red: lo permitido"
check "ui -> catalog"            'abierto ui catalog 80'
check "ui -> checkout"           'abierto ui checkout 80'
check "checkout -> orders"       'abierto checkout orders 80'
check "catalog -> catalog-db"    'abierto catalog catalog-db 3306'
check "orders -> orders-db"      'abierto orders orders-db 5432'
check "checkout -> checkout-db"  'abierto checkout checkout-db 6379'

echo "5) Segmentacion de red: lo bloqueado"
check "ui NO llega a orders-db (frontend -> datos)"      'bloqueado ui orders-db 5432'
check "carts NO llega a orders-db (no es su base)"       'bloqueado carts orders-db 5432'
check "checkout NO llega a catalog-db (no es su base)"   'bloqueado checkout catalog-db 3306'
kubectl delete pod intruso -n $NS --ignore-not-found --wait=true >/dev/null 2>&1
kubectl run intruso -n $NS --image=busybox:1.37 --restart=Never --command -- sleep 120 >/dev/null 2>&1
kubectl wait -n $NS --for=condition=Ready pod/intruso --timeout=90s >/dev/null 2>&1
check "un pod ajeno NO llega a catalog"    '! kubectl exec -n $NS intruso -- nc -z -w 3 catalog 80 2>/dev/null'
check "un pod ajeno NO llega a la ui"      '! kubectl exec -n $NS intruso -- nc -z -w 3 ui 80 2>/dev/null'
check "un pod ajeno NO llega a orders-db"  '! kubectl exec -n $NS intruso -- nc -z -w 3 orders-db 5432 2>/dev/null'
kubectl delete pod intruso -n $NS --wait=false >/dev/null 2>&1

echo
echo "Resultado: $OK verificaciones OK, $FALLA fallidas"
[ "$FALLA" -eq 0 ]
