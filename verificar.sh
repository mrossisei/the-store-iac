#!/usr/bin/env bash
# Verifica que el entorno desplegado en AWS funcione: la tienda responde por
# el balanceador, se puede completar una compra, la orden persiste en RDS, las
# reglas de red del cluster permiten solo lo declarado y las bases de datos no
# son alcanzables desde Internet.
#
# Uso (desde la raiz del repositorio): ./verificar.sh
set -uo pipefail
cd "$(dirname "$0")"
REGION=$(terraform -chdir=terraform output -raw kubeconfig_command | sed 's/.*--region //')
CLUSTER=$(terraform -chdir=terraform output -raw kubeconfig_command | sed 's/.*--name \([^ ]*\).*/\1/')
BASE=$(terraform -chdir=terraform output -raw url)
MYSQL=$(terraform -chdir=terraform output -json databases | grep -o '"mysql": *"[^"]*"' | cut -d'"' -f4)
NS=the-store
PRODUCTO=d27cf49f-b689-4a75-a249-d373e0330bb5   # "The Quiet Quill", $150
OK=0; FALLA=0; J=""
check() { if eval "$2"; then echo "  OK    $1"; OK=$((OK+1)); else echo "  FALLA $1"; FALLA=$((FALLA+1)); fi; }

# kubectl contra el cluster EKS (usa las credenciales de la CLI de AWS).
export KUBECONFIG=$(mktemp); trap 'rm -f $KUBECONFIG $J' EXIT
aws eks update-kubeconfig --name "$CLUSTER" --region "$REGION" >/dev/null

# Sonda de conectividad desde un microservicio: exit 28 de curl = timeout =
# bloqueado. Los Services de la aplicacion escuchan en el puerto 80.
abierto()   { kubectl exec -n $NS deploy/$1 -- curl -s -m 3 -o /dev/null "http://$2:$3/" >/dev/null 2>&1; [ $? -ne 28 ]; }
bloqueado() { ! abierto "$@"; }

echo "Tienda: $BASE"
echo "1) Estado del cluster"
check "los nodos worker estan Ready (al menos 2)"     '[ "$(kubectl get nodes --no-headers | grep -c " Ready")" -ge 2 ]'
check "los 10 pods de la aplicacion estan corriendo"  '[ "$(kubectl get pods -n $NS --no-headers | grep -c Running)" -ge 10 ]'

echo "2) La tienda responde a traves del balanceador"
check "la pagina principal responde 200"  '[ "$(curl -s -o /dev/null -m 15 -w %{http_code} $BASE/)" = 200 ]'
check "el catalogo lista 6 productos"     '[ "$(curl -s -m 15 $BASE/catalog | grep -c product-name)" = 6 ]'

echo "3) Compra completa y persistencia"
J=$(mktemp)
curl -s -o /dev/null -m 15 -b $J -c $J -X POST $BASE/cart --data-urlencode productId=$PRODUCTO --data-urlencode quantity=1
check "el producto entra al carrito (DynamoDB)" 'curl -s -m 15 -b $J -c $J $BASE/cart | tr -d "\n" | grep -q "The Quiet Quill"'
curl -s -o /dev/null -m 15 -b $J -c $J $BASE/checkout
curl -s -o /dev/null -m 15 -b $J -c $J -X POST $BASE/checkout --data-urlencode firstName=John --data-urlencode lastName=Doe \
  --data-urlencode email=john@example.com --data-urlencode address1="100 Main Street" --data-urlencode city=Anytown \
  --data-urlencode zipCode=11111 --data-urlencode state=CA
curl -s -o /dev/null -m 15 -b $J -c $J -X POST $BASE/checkout/delivery --data-urlencode token=priority-mail
check "la orden se confirma por \$165" 'curl -s -m 30 -b $J -c $J -X POST $BASE/checkout/payment --data-urlencode "cardHolder=John Doe" \
  --data-urlencode cardNumber=1234567890123456 --data-urlencode expiryDate=01/35 --data-urlencode cvc=123 | tr -d "\n" | grep -q "\$165"'
check "la orden quedo guardada en PostgreSQL (RDS)" 'kubectl exec -n $NS deploy/ui -- curl -s -m 5 http://orders/orders | grep -q createdDate'

echo "4) Segmentacion de red dentro del cluster"
check "ui -> catalog (permitido)"       'abierto ui catalog 80'
check "ui -> checkout (permitido)"      'abierto ui checkout 80'
check "checkout -> orders (permitido)"  'abierto checkout orders 80'
kubectl delete pod intruso -n $NS --ignore-not-found --wait=true >/dev/null 2>&1
kubectl run intruso -n $NS --image=busybox:1.37 --restart=Never --command -- sleep 120 >/dev/null 2>&1
kubectl wait -n $NS --for=condition=Ready pod/intruso --timeout=120s >/dev/null 2>&1
check "un pod ajeno NO llega a catalog"  '! kubectl exec -n $NS intruso -- nc -z -w 3 catalog 80 2>/dev/null'
check "un pod ajeno NO llega a la ui"    '! kubectl exec -n $NS intruso -- nc -z -w 3 ui 80 2>/dev/null'
kubectl delete pod intruso -n $NS --wait=false >/dev/null 2>&1

echo "5) Capa de datos (security groups)"
check "catalog llega a su base MySQL en RDS"          'abierto catalog ${MYSQL%%:*} 3306'
check "la base MySQL NO es alcanzable desde Internet"  'curl -s -m 5 -o /dev/null "http://$MYSQL/" >/dev/null 2>&1; case $? in 6|7|28) true;; *) false;; esac'

echo
echo "Resultado: $OK verificaciones OK, $FALLA fallidas"
[ "$FALLA" -eq 0 ]
