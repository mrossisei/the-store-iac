#!/usr/bin/env bash
# Smoke test HTTP de The Store: reproduce con curl el mismo flujo que los
# tests e2e de Cypress (home, catálogo, detalle, carrito, checkout completo).
# Uso: scripts/smoke-test.sh http://the-store.localhost
set -uo pipefail
BASE="${1:?uso: $0 <url base>}"
JAR=$(mktemp); trap 'rm -f "$JAR"' EXIT
PRODUCT="d27cf49f-b689-4a75-a249-d373e0330bb5"   # "The Quiet Quill" - $150
PASS=0; FAILN=0
# Con HTTPS se acepta el certificado autofirmado generado por Terraform.
case "$BASE" in https://*) K="-k" ;; *) K="" ;; esac
check() { if eval "$2"; then printf "  \033[32m✔\033[0m %s\n" "$1"; PASS=$((PASS+1)); else printf "  \033[31m✘\033[0m %s\n" "$1"; FAILN=$((FAILN+1)); fi; }
# Las respuestas se aplanan a una sola línea para poder buscar atributos HTML con grep.
get()  { curl -s $K -L -m 20 -b "$JAR" -c "$JAR" "$BASE$1" | tr -d '\n'; }
post() { curl -s $K -L -m 20 -b "$JAR" -c "$JAR" -X POST "$BASE$1" "${@:2}" | tr -d '\n'; }

echo "Smoke test contra $BASE"
code=$(curl -s $K -o /dev/null -m 20 -w '%{http_code}' "$BASE/")
check "GET / responde 200 (obtenido $code)" '[ "$code" = "200" ]'

home=$(get /home)
check "Home muestra el botón 'Shop Now'" 'echo "$home" | grep -q "shop-now"'

catalog=$(get /catalog)
n=$(echo "$catalog" | grep -o 'class="[^"]*product-name' | wc -l)
check "Catálogo lista 6 productos (obtenidos $n)" '[ "$n" = "6" ]'
check "Primer producto es 'Aqua Ace GT'" 'echo "$catalog" | grep -q "Aqua Ace GT"'

detail=$(get "/catalog/$PRODUCT")
check "Detalle del producto muestra 'The Quiet Quill'" 'echo "$detail" | grep -q "The Quiet Quill"'

post /cart --data-urlencode "productId=$PRODUCT" --data-urlencode "quantity=1" >/dev/null
cart=$(get /cart)
check "Carrito contiene 'The Quiet Quill'" 'echo "$cart" | grep -q "The Quiet Quill"'
check "Subtotal del carrito es \$150" 'echo "$cart" | grep -q "\$150"'

shipping=$(get /checkout)
check "Checkout (dirección) responde" 'echo "$shipping" | grep -qi "firstName"'

delivery=$(post /checkout --data-urlencode firstName=John --data-urlencode lastName=Doe \
  --data-urlencode email=john_doe@example.com --data-urlencode address1="100 Main Street" \
  --data-urlencode city=Anytown --data-urlencode zipCode=11111 --data-urlencode state=CA)
token=$(echo "$delivery" | grep -oE 'name="token"[^>]*value="[^"]+"' | head -1 | sed -E 's/.*value="([^"]+)".*/\1/')
check "Checkout (envío) ofrece opciones de entrega (token=${token:-?})" '[ -n "$token" ]'

payment=$(post /checkout/delivery --data-urlencode "token=$token")
check "Checkout (pago) responde" 'echo "$payment" | grep -qi "cardNumber"'

order=$(post /checkout/payment --data-urlencode "cardHolder=John Doe" --data-urlencode cardNumber=1234567890123456 \
  --data-urlencode expiryDate=01/35 --data-urlencode cvc=123)
check "Orden confirmada: subtotal \$150" 'echo "$order" | grep -q "\$150"'
check "Orden confirmada: envío \$10" 'echo "$order" | grep -q "\$10"'
check "Orden confirmada: total \$165" 'echo "$order" | grep -q "\$165"'

echo; echo "Resultado: $PASS OK, $FAILN fallidos"
[ "$FAILN" -eq 0 ]
