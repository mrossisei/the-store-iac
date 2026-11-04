#!/usr/bin/env bash
# T10: verificación explícita de dos kind.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")" && pwd)
command -v python3 >/dev/null || { echo 'Falta python3' >&2; exit 1; }
exec python3 "$ROOT/scripts/verificar.py" "$@"
