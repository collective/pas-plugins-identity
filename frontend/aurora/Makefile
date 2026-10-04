### Defensive settings for make:
#     https://tech.davis-hansson.com/p/make/
SHELL:=bash
.ONESHELL:
.SHELLFLAGS:=-eu -o pipefail -c
.SILENT:
.DELETE_ON_ERROR:
MAKEFLAGS+=--warn-undefined-variables
MAKEFLAGS+=--no-builtin-rules

CURRENT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

# Recipe snippets for reuse

# We like colors
# From: https://coderwall.com/p/izxssa/colored-makefile-for-golang-projects
RED=`tput setaf 1`
GREEN=`tput setaf 2`
RESET=`tput sgr0`
YELLOW=`tput setaf 3`

GIT_FOLDER=$(CURRENT_DIR)/.git


ADDON_NAME='@plone-collective/aurora-identity'

.PHONY: help
help: ## Show this help
	@echo -e "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)"

# Dev Helpers

.PHONY: install
install: ## Install Aurora and the add-on for development
	@echo "$(GREEN)Install$(RESET)"
	pnpm dlx mrs-developer missdev --no-config --fetch-https
	pnpm i
	make build-deps

.PHONY: start
start: ## Start Aurora on http://localhost:3000, reloading the add-on on change
	pnpm start

.PHONY: build
build: ## Build a production bundle of Aurora with the add-on
	pnpm build

core/packages/registry/dist: $(shell find core/packages/registry/src -type f)
	pnpm --filter @plone/registry build

core/packages/icons/dist: $(shell find core/packages/icons/src -type f)
	pnpm --filter @plone/icons build

core/packages/quanta/dist: $(shell find core/packages/quanta/src -type f)
	pnpm --filter @plone/quanta build

core/packages/components/dist: $(shell find core/packages/components/src -type f)
	pnpm --filter @plone/components build

core/packages/client/dist: $(shell find core/packages/client/src -type f)
	pnpm --filter @plone/client build

core/packages/helpers/dist: $(shell find core/packages/helpers/src -type f)
	pnpm --filter @plone/helpers build

core/packages/react-router/dist: $(shell find core/packages/react-router/src -type f)
	pnpm --filter @plone/react-router build

.PHONY: build-deps
build-deps: core/packages/registry/dist core/packages/icons/dist core/packages/quanta/dist core/packages/components/dist core/packages/client/dist core/packages/react-router/dist core/packages/helpers/dist ## Build Aurora's library packages

.PHONY: i18n
i18n: ## Regenerate the add-on's catalogues from identity-core's
	pnpm --filter $(ADDON_NAME) i18n

.PHONY: ci-i18n
ci-i18n: ## Check the add-on's catalogues match identity-core's
	pnpm --filter $(ADDON_NAME) i18n && git diff --exit-code -- ../packages/aurora-identity/locales

.PHONY: format
format: ## Format the add-on
	pnpm prettier:fix
	pnpm lint:fix
	pnpm stylelint:fix

.PHONY: lint
lint: ## Lint and typecheck the add-on
	pnpm lint
	pnpm typecheck
	pnpm prettier
	pnpm stylelint --allow-empty-input

.PHONY: test
test: ## Run the add-on's unit tests
	pnpm test

.PHONY: ci-test
ci-test: ## Run the add-on's unit tests once
	CI=1 pnpm test --run

# Acceptance: a real sign-in, through Dex, against the backend's acceptance
# server. Start the three services, each in its own shell, register the
# provider, then run the tests.

ACCEPTANCE_API_PATH=http://localhost:55001/plone
DEX_CONFIG=$(CURRENT_DIR)/../../backend/tests/_resources/dex/config.yaml

.PHONY: acceptance-backend-start
acceptance-backend-start: ## Start the backend's acceptance server on http://localhost:55001/plone
	$(MAKE) -C ../../backend acceptance-backend-start

.PHONY: acceptance-dex-start
acceptance-dex-start: ## Start Dex with the backend's test configuration on http://127.0.0.1:5556/dex
	docker run --rm --name aurora-acceptance-dex -p 5556:5556 -v $(DEX_CONFIG):/etc/dex/config.yaml:ro ghcr.io/dexidp/dex:v2.44.0 dex serve /etc/dex/config.yaml

.PHONY: acceptance-frontend-start
acceptance-frontend-start: ## Build Aurora and serve it on http://localhost:3000 against the acceptance backend
	pnpm build
	PLONE_API_PATH=$(ACCEPTANCE_API_PATH) pnpm start:prod

.PHONY: acceptance-provider
acceptance-provider: ## Register the Dex provider on the acceptance backend
	PLONE_API_PATH=$(ACCEPTANCE_API_PATH) pnpm acceptance-provider

.PHONY: acceptance-test
acceptance-test: ## Run the acceptance tests
	pnpm acceptance-test
