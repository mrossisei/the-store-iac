#!/usr/bin/env python3
"""Valida terraform show -json de una transición de cuarentena; no muestra datos."""
import argparse
import json
from pathlib import Path


def validate(plan):
    changes = [resource for resource in plan.get('resource_changes', []) if resource['change']['actions'] != ['no-op'] and resource.get('mode', 'managed') == 'managed']
    if not changes:
        raise ValueError('El plan no contiene cambios; no demuestra una transición de cuarentena')
    if any(resource['type'] != 'kubernetes_network_policy_v1' for resource in changes):
        raise ValueError('El plan modifica recursos distintos de NetworkPolicy')
    if any(resource['change'].get('replace_paths') or {'create', 'delete'}.issubset(resource['change']['actions']) for resource in changes):
        raise ValueError('El plan reemplaza recursos; revisar namespaces y selectores')
    # Providers can still read data sources; no application resources may change.
    return len(changes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan_json', help='Archivo privado obtenido con terraform show -json PLAN')
    args = parser.parse_args()
    count = validate(json.loads(Path(args.plan_json).read_text()))
    print(f'PASS: {count} cambios; únicamente NetworkPolicies')


if __name__ == '__main__':
    main()
