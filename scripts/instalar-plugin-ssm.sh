#!/usr/bin/env bash
# Instalación local de usuario, sin sudo ni cambios en el perfil de shell.
set -euo pipefail
command -v session-manager-plugin >/dev/null && { session-manager-plugin --version; exit 0; }
[ "$(uname -m)" = x86_64 ] || { echo 'Este instalador requiere Linux x86_64' >&2; exit 1; }
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
ROOT=$(cd "$(dirname "$0")/.." && pwd)
VERSION=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ssm_plugin_version"])' "$ROOT/config/herramientas.json")
SHA=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["ssm_plugin_sha256"])' "$ROOT/config/herramientas.json")
URL="https://session-manager-downloads.s3.us-east-1.amazonaws.com/plugin/$VERSION/ubuntu_64bit/session-manager-plugin.deb"
# Reanudar en cada intento: el endpoint S3 del paquete puede transferir lento.
DOWNLOADED=false
for attempt in 1 2 3 4 5; do
  if curl -4 -fLsS -C - --connect-timeout 15 --max-time 120 "$URL" -o "$WORK/plugin.deb"; then
    DOWNLOADED=true
    break
  fi
done
$DOWNLOADED || { echo 'No se pudo completar la descarga oficial del plugin.' >&2; exit 1; }
echo "$SHA  $WORK/plugin.deb" | sha256sum -c -
DEST="${XDG_DATA_HOME:-$HOME/.local/share}/the-store/session-manager-plugin"
mkdir -p "$DEST" "$HOME/.local/bin"
dpkg-deb -x "$WORK/plugin.deb" "$DEST"
ln -s "$DEST/usr/local/sessionmanagerplugin/bin/session-manager-plugin" "$HOME/.local/bin/session-manager-plugin"
"$HOME/.local/bin/session-manager-plugin" --version
echo 'El ejecutable está en ~/.local/bin; agregar esa carpeta al PATH si hace falta.'
