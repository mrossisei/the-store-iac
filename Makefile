# ---------------------------------------------------------------------------
# The Store - Infraestructura como Código con Terraform (ITBA - Redes 2C 2026)
#
# Uso rápido:
#   make up                # plataforma + imágenes + entornos dev y prod
#   make app ENV=prod      # sólo (re)aplica un entorno
#   make plan ENV=prod     # muestra el plan de un entorno
#   make smoke ENV=prod    # smoke test HTTP del entorno
#   make down              # destruye todo (en orden inverso)
# ---------------------------------------------------------------------------
SHELL      := /bin/bash
TF         ?= terraform
ENV        ?= dev
ROOT       := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
TF_DIR     := $(ROOT)/terraform
PLATFORM   := $(TF_DIR)/1-platform
IMAGES     := $(TF_DIR)/2-images
APP        := $(TF_DIR)/3-app
VARFILE    := $(TF_DIR)/environments/$(ENV).tfvars
KUBECONFIG ?= $(HOME)/.kube/the-store.kubeconfig
export KUBECONFIG

.PHONY: help prereqs init fmt validate platform images app app-all up plan down destroy-app destroy-images destroy-platform \
        status smoke netpol-test drift-demo persistence-test e2e load kubeconfig outputs graph

help: ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

prereqs: ## Verifica requisitos (docker, terraform, puertos, disco, sysctl)
	@bash $(ROOT)/scripts/check-prereqs.sh

init: ## terraform init en las tres capas
	@cd $(PLATFORM) && $(TF) init -input=false
	@cd $(IMAGES)   && $(TF) init -input=false
	@cd $(APP)      && $(TF) init -input=false

fmt: ## terraform fmt -recursive
	@cd $(TF_DIR) && $(TF) fmt -recursive

validate: init ## terraform validate en las tres capas
	@cd $(PLATFORM) && $(TF) validate
	@cd $(IMAGES)   && $(TF) validate
	@cd $(APP)      && $(TF) validate

platform: ## Capa 1: red, registry, clúster kind, ingress-nginx, metrics-server
	@cd $(PLATFORM) && $(TF) init -input=false >/dev/null && $(TF) apply -input=false -auto-approve

images: ## Capa 2: build + push de las imágenes al registry local
	@cd $(IMAGES) && $(TF) init -input=false >/dev/null && $(TF) apply -input=false -auto-approve

app: ## Capa 3: despliega el entorno $(ENV) (dev|prod)
	@cd $(APP) && $(TF) init -input=false >/dev/null \
	  && $(TF) workspace select -or-create $(ENV) >/dev/null \
	  && $(TF) apply -input=false -auto-approve -var-file=$(VARFILE)

app-all: ## Capa 3: despliega dev y prod
	@$(MAKE) app ENV=dev
	@$(MAKE) app ENV=prod

up: prereqs platform images app-all status ## Todo: plataforma + imágenes + dev + prod

plan: ## Plan del entorno $(ENV) (no aplica nada)
	@cd $(APP) && $(TF) workspace select -or-create $(ENV) >/dev/null \
	  && $(TF) plan -input=false -var-file=$(VARFILE)

outputs: ## Outputs del entorno $(ENV)
	@cd $(APP) && $(TF) workspace select $(ENV) >/dev/null && $(TF) output

destroy-app: ## Destruye el entorno $(ENV)
	@cd $(APP) && $(TF) workspace select $(ENV) >/dev/null \
	  && $(TF) destroy -input=false -auto-approve -var-file=$(VARFILE)

destroy-images: ## Destruye la capa 2 (el registry conserva las imágenes: keep_remotely)
	@cd $(IMAGES) && $(TF) destroy -input=false -auto-approve

destroy-platform: ## Destruye la capa 1 (clúster, registry y red)
	@cd $(PLATFORM) && $(TF) destroy -input=false -auto-approve

down: ## Destruye todo en orden inverso (prod, dev, imágenes, plataforma)
	-@$(MAKE) destroy-app ENV=prod
	-@$(MAKE) destroy-app ENV=dev
	-@$(MAKE) destroy-images
	@$(MAKE) destroy-platform

status: ## Estado del clúster y de los entornos
	@echo "== nodos =="; kubectl get nodes -o wide
	@echo; echo "== entornos =="; kubectl get ns -l app.kubernetes.io/part-of=the-store
	@for ns in $$(kubectl get ns -l app.kubernetes.io/part-of=the-store -o name | cut -d/ -f2); do \
	  echo; echo "== $$ns =="; kubectl get deploy,sts,svc,ingress,hpa,netpol -n $$ns; done

kubeconfig: ## Imprime el export de KUBECONFIG para usar kubectl
	@echo "export KUBECONFIG=$(KUBECONFIG)"

smoke: ## Smoke test HTTP (home, catálogo, carrito, checkout) contra el entorno $(ENV)
	@bash $(ROOT)/scripts/smoke-test.sh "$$(cd $(APP) && $(TF) workspace select $(ENV) >/dev/null && $(TF) output -raw url)"

netpol-test: ## Verifica las NetworkPolicies del entorno $(ENV)
	@bash $(ROOT)/scripts/netpol-test.sh the-store-$(ENV)

drift-demo: ## Demo de detección de drift en el entorno $(ENV)
	@bash $(ROOT)/scripts/drift-demo.sh $(ENV)

persistence-test: ## Verifica persistencia de órdenes tras reiniciar el pod de orders ($(ENV))
	@bash $(ROOT)/scripts/persistence-test.sh the-store-$(ENV)

e2e: ## Tests e2e oficiales (Cypress en Docker, ~2,5 GB de imagen) contra $(ENV)
	@bash $(ROOT)/the-store/src/e2e/scripts/run-docker.sh -n host "$$(cd $(APP) && $(TF) workspace select $(ENV) >/dev/null && $(TF) output -raw url)"

load: ## Generador de carga (Artillery en Docker) contra $(ENV) durante 120 s
	@bash $(ROOT)/the-store/src/load-generator/scripts/run-docker.sh -n host -t "$$(cd $(APP) && $(TF) workspace select $(ENV) >/dev/null && $(TF) output -raw url)" -d 120 --vu 5

graph: ## Grafo de dependencias de la capa 3 (requiere graphviz: dot)
	@cd $(APP) && $(TF) graph | dot -Tsvg > $(ROOT)/docs/img/graph-app.svg && echo "docs/img/graph-app.svg"
