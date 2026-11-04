#!/usr/bin/env bash
# Da a los nodos kind un token de ECR obtenido con LabRole. El token dura 12 horas
# y un timer lo renueva. Se escribe sobre el mismo archivo porque está montado en
# los nodos como /var/lib/kubelet/config.json.
set -euo pipefail
region=$(python3 -c 'import json; print(json.load(open("/opt/the-store/config.json"))["region"])')
read -r endpoint token < <(aws ecr get-authorization-token --region "$region" \
  --query 'authorizationData[0].[proxyEndpoint,authorizationToken]' --output text)
printf '{"auths":{"%s":{"auth":"%s"}}}\n' "${endpoint#https://}" "$token" > /var/lib/the-store/docker-config.json
