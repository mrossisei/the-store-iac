#!/usr/bin/env python3
"""Data source external: stdout es únicamente JSON de paths/contextos/UID, nunca credenciales."""
import json
import sys
from acceso_kind import ROOT, private_write, validate_manifest

try:
    query = json.load(sys.stdin)
    print(json.dumps(validate_manifest(query['manifest'])))
except Exception as exc:
    # Diagnóstico privado sin devolver certificados ni stdout de kubectl.
    try:
        private_write(ROOT / '.local/acceso-error.log', type(exc).__name__ + ': ' + str(exc) + '\n')
    except OSError:
        pass
    print('Acceso kind inválido: iniciar scripts/acceso.py run y comprobar ambos túneles, destinos y certificados.', file=sys.stderr)
    sys.exit(1)
