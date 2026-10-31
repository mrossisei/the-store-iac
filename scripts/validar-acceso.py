#!/usr/bin/env python3
"""Data source external: stdout es únicamente JSON de paths/contextos/UID, nunca credenciales."""
import json
import sys
from acceso_kind import validate_manifest

try:
    query = json.load(sys.stdin)
    print(json.dumps(validate_manifest(query['manifest'])))
except Exception:
    print('Acceso kind inválido: iniciar scripts/acceso.py run y comprobar ambos túneles, destinos y certificados.', file=sys.stderr)
    sys.exit(1)
