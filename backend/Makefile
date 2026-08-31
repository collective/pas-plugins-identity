### Defensive settings for make:
#     https://tech.davis-hansson.com/p/make/
SHELL:=bash
.ONESHELL:
.SHELLFLAGS:=-xeu -o pipefail -O inherit_errexit -c
.SILENT:
.DELETE_ON_ERROR:
MAKEFLAGS+=--warn-undefined-variables
MAKEFLAGS+=--no-builtin-rules

# We like colors
# From: https://coderwall.com/p/izxssa/colored-makefile-for-golang-projects
RED=`tput setaf 1`
GREEN=`tput setaf 2`
RESET=`tput sgr0`
YELLOW=`tput setaf 3`

# Python checks
UV?=uv

# installed?
ifeq (, $(shell which $(UV) ))
  $(error "UV=$(UV) not found in $(PATH)")
endif

REPOSITORY_SETTINGS := $(shell uvx repoplone settings dump)
IMAGE_NAME_PREFIX := $(shell echo '$(REPOSITORY_SETTINGS)' | jq -r '.container_images_prefix')
IMAGE_NAME_SEPARATOR := -
IMAGE_NAME_PREFIX_WITH_SEPARATOR := $(IMAGE_NAME_PREFIX)$(IMAGE_NAME_SEPARATOR)

IMAGE_TAG=latest
IMAGE_NAME=$(IMAGE_NAME_PREFIX_WITH_SEPARATOR)backend:$(IMAGE_TAG)

PLONE_SITE_ID=Plone
BACKEND_FOLDER=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
EXAMPLE_CONTENT_FOLDER := $(shell echo '$(REPOSITORY_SETTINGS)' | jq -r '.backend.code_path')/setuphandlers/examplecontent
PACKAGE_NAME := $(shell echo '$(REPOSITORY_SETTINGS)' | jq -r '.backend.name')

VENV_FOLDER=$(BACKEND_FOLDER)/.venv
export VIRTUAL_ENV=$(VENV_FOLDER)
BIN_FOLDER=$(VENV_FOLDER)/bin

# Environment variables to be exported
export PYTHONWARNINGS := ignore
export DOCKER_BUILDKIT := 1
export PYTHON_VERSION := 3.14
export PLONE_VERSION := $(shell echo '$(REPOSITORY_SETTINGS)' | jq -r '.backend.base_package_version')
export ENABLE_PRINTING_MAILHOST := true


ifdef CI
UV_VENV_ARGS :=
else
UV_VENV_ARGS := --python=$(PYTHON_VERSION)
endif


all: build

# Add the following 'help' target to your Makefile
# And add help text after each target name starting with '\#\#'
.PHONY: help
help: ## This help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


.PHONY: debug-settings
debug-settings:  ## Debug settings
	@echo "PLONE_VERSION: $(PLONE_VERSION)"
	@echo "PACKAGE_NAME: $(PACKAGE_NAME)"
	@echo "EXAMPLE_CONTENT_FOLDER: $(EXAMPLE_CONTENT_FOLDER)"
	@echo "IMAGE_NAME_PREFIX_WITH_SEPARATOR: $(IMAGE_NAME_PREFIX_WITH_SEPARATOR)"
	@echo "IMAGE_NAME: $(IMAGE_NAME)"


requirements-mxdev.txt: pyproject.toml mx.ini ## Generate constraints file
	@echo "$(GREEN)==> Generate constraints file$(RESET)"
	@echo '-c https://dist.plone.org/release/$(PLONE_VERSION)/constraints.txt' > requirements.txt
	@uvx 'mxdev[uv]' -c mx.ini

$(VENV_FOLDER): requirements-mxdev.txt ## Install dependencies
	@echo "$(GREEN)==> Install environment$(RESET)"
	@if [[ -d "$(VENV_FOLDER)" ]]; then echo "$(YELLOW)==> Environment already exists at $(VENV_FOLDER)$(RESET)"; else uv venv $(UV_VENV_ARGS) $(VENV_FOLDER); fi
	@uv pip install -r requirements-mxdev.txt

.PHONY: sync
sync: $(VENV_FOLDER) ## Sync project dependencies
	@echo "$(GREEN)==> Sync project dependencies$(RESET)"
	@uv pip install -r requirements-mxdev.txt

instance/etc/zope.ini instance/etc/zope.conf: instance.yaml ## Create instance configuration
	@echo "$(GREEN)==> Create instance configuration$(RESET)"
	@uvx cookiecutter -f --no-input -c 2.4.1 --config-file instance.yaml gh:plone/cookiecutter-zope-instance

.PHONY: config
config: instance/etc/zope.ini

# `install-demo` is part of this, not an optional afterthought: two test
# modules import `identitydemo` at module scope, and a conftest that cannot
# import aborts the whole pytest session rather than skipping a directory. An
# environment built by `make install` has to be one the suite can collect in.
#
# It does not reach the published package or the production image. Neither
# runs `make install` -- the Dockerfile drives mxdev directly -- and the demo
# stays out of `mx.ini` for exactly that reason.
.PHONY: install
install: $(VENV_FOLDER) config install-demo ## Install Plone and dependencies

# Optional dependency layers. The base install is core-only on purpose, so
# the CI matrix layers the extra on top: core / +server.
EXTRAS ?=

.PHONY: install-extras
install-extras: $(VENV_FOLDER) ## Layer optional extras on top, e.g. EXTRAS=server
	@if [ -z "$(EXTRAS)" ]; then \
		echo "$(YELLOW)==> No extras requested; core-only install$(RESET)"; \
	else \
		echo "$(GREEN)==> Install extras: $(EXTRAS)$(RESET)"; \
		uv pip install -c constraints-mxdev.txt -e ".[test,$(EXTRAS)]"; \
	fi

# The federation demo stack. Installed explicitly rather than from
# an mx.ini source: `Dockerfile` copies the whole tree and runs mxdev, so a
# source section here would put the demo profiles -- and their published
# client secret -- into the production image's portal_setup. The one place
# that must never happen is the one place nobody would look.
.PHONY: install-demo
install-demo: $(VENV_FOLDER) ## Install the federation demo package (never published)
	@echo "$(GREEN)==> Install the federation demo$(RESET)"
	@uv pip install -c constraints-mxdev.txt -e "./demo"

.PHONY: clean
clean: ## Clean installation and instance
	@echo "$(RED)==> Cleaning environment and build$(RESET)"
	@rm -rf $(VENV_FOLDER) pyvenv.cfg .installed.cfg instance/etc .venv .pytest_cache .ruff_cache constraints* requirements*

.PHONY: remove-data
remove-data: ## Remove all content
	@echo "$(RED)==> Removing all content$(RESET)"
	rm -rf $(VENV_FOLDER) instance/var

.PHONY: start
start: $(VENV_FOLDER) instance/etc/zope.ini ## Start a Plone instance on localhost:8080
	@$(BIN_FOLDER)/runwsgi instance/etc/zope.ini

.PHONY: console
console: $(VENV_FOLDER) instance/etc/zope.ini ## Start a console into a Plone instance
	@$(BIN_FOLDER)/zconsole debug instance/etc/zope.conf

.PHONY: create-site
create-site: $(VENV_FOLDER) instance/etc/zope.ini ## Create a new site from scratch
	@$(BIN_FOLDER)/zconsole run instance/etc/zope.conf ./scripts/create_site.py

# Example Content
.PHONY: update-example-content
update-example-content: $(VENV_FOLDER) ## Export example content inside package
	@echo "$(GREEN)==> Export example content into $(EXAMPLE_CONTENT_FOLDER) $(RESET)"
	if [ -d $(EXAMPLE_CONTENT_FOLDER)/content ]; then rm -r $(EXAMPLE_CONTENT_FOLDER)/* ;fi
	@$(BIN_FOLDER)/plone-exporter instance/etc/zope.conf $(PLONE_SITE_ID) $(EXAMPLE_CONTENT_FOLDER)

# QA
.PHONY: lint
lint: ## Check and fix code base according to Plone standards
	@echo "$(GREEN)==> Lint codebase$(RESET)"
	@uvx ruff@latest check --fix --config $(BACKEND_FOLDER)/pyproject.toml
	@uvx pyroma@latest -d .
	@uvx check-python-versions@latest .
	@uvx zpretty@latest --check src demo

.PHONY: format
format: ## Check and fix code base according to Plone standards
	@echo "$(GREEN)==> Format codebase$(RESET)"
	@uvx ruff@latest check --select I --fix --config $(BACKEND_FOLDER)/pyproject.toml
	@uvx ruff@latest format --config $(BACKEND_FOLDER)/pyproject.toml
	@uvx zpretty@latest -i src demo

############################################
# Dex, the OIDC provider for the flow tests
############################################
# pytest-docker starts and stops this stack on demand, so `make test` needs
# none of these. They are for driving the provider by hand -- poking at its
# discovery document, reading its logs. Stop it before running the suite: the
# port is fixed, so a hand-started Dex and pytest-docker's own cannot coexist.
COMPOSE_FILE=$(BACKEND_FOLDER)/tests/docker-compose.yml

.PHONY: dex-start
dex-start: ## Start Dex by hand on localhost:5556
	@echo "$(GREEN)==> Start Dex$(RESET)"
	@docker compose -f $(COMPOSE_FILE) up -d

.PHONY: dex-status
dex-status: ## Show the Dex stack status
	@echo "$(GREEN)==> Dex status$(RESET)"
	@docker compose -f $(COMPOSE_FILE) ps

.PHONY: dex-stop
dex-stop: ## Stop Dex
	@echo "$(RED)==> Stop Dex$(RESET)"
	@docker compose -f $(COMPOSE_FILE) down

.PHONY: check-pragmas
check-pragmas: ## Every coverage pragma carries a reason on the same line
	@echo "$(GREEN)==> Check coverage pragmas$(RESET)"
	@$(BIN_FOLDER)/python scripts/check_pragmas.py

.PHONY: check-clean-install
check-clean-install: requirements-mxdev.txt ## Import the package from a no-extras install
	@echo "$(GREEN)==> Check that the no-extras install imports$(RESET)"
	@# Joined with && rather than ;: macOS ships GNU Make 3.81, which ignores
	@# both .ONESHELL and .SHELLFLAGS' -e, so a ;-chain would report the exit
	@# status of the trailing rm and the check could never fail.
	@rm -rf $(BACKEND_FOLDER)/.venv-clean && \
	uv venv $(UV_VENV_ARGS) $(BACKEND_FOLDER)/.venv-clean && \
	VIRTUAL_ENV=$(BACKEND_FOLDER)/.venv-clean uv pip install -q -c constraints-mxdev.txt . && \
	$(BACKEND_FOLDER)/.venv-clean/bin/python -c "import pas.plugins.identity.core.flows; print('no-extras import OK')" && \
	rm -rf $(BACKEND_FOLDER)/.venv-clean

.PHONY: check-imports
check-imports: ## Enforce the core/server layer boundary
	@echo "$(GREEN)==> Check layer boundaries$(RESET)"
	@# Run against a venv holding nothing but this package. The migration
	@# test dependencies (pas.plugins.authomatic, pas.plugins.oidc) each ship a
	@# pas/__init__.py declaring a pkg_resources namespace and do *not* declare
	@# it in their dist-info, so horse-with-no-namespace cannot neutralise it.
	@# With those installed, `pas.plugins` stops being a PEP 420 namespace and
	@# grimp refuses to build a graph rooted at pas.plugins.identity at all --
	@# silently, with a banner and a non-zero exit and no message.
	@# The contract is a property of this package's own source, so checking it
	@# in isolation is the more honest thing anyway. --no-deps keeps it quick.
	@# grimp is pinned below 3.16: that release ships no wheel for the
	@# Python this venv is built with, so uv falls back to building it
	@# and maturin fails for want of a Rust toolchain. The failed
	@# install leaves an empty venv behind, so the symptom is a missing
	@# `lint-imports` rather than anything mentioning wheels.
	@rm -rf $(BACKEND_FOLDER)/.venv-imports && \
	uv venv $(UV_VENV_ARGS) $(BACKEND_FOLDER)/.venv-imports && \
	VIRTUAL_ENV=$(BACKEND_FOLDER)/.venv-imports uv pip install -q "grimp<3.16" import-linter && \
	VIRTUAL_ENV=$(BACKEND_FOLDER)/.venv-imports uv pip install -q --no-deps . && \
	$(BACKEND_FOLDER)/.venv-imports/bin/lint-imports --config pyproject.toml && \
	rm -rf $(BACKEND_FOLDER)/.venv-imports

# i18n
.PHONY: i18n
i18n: $(VENV_FOLDER) ## Update locales
	@echo "$(GREEN)==> Updating locales$(RESET)"
	@$(BIN_FOLDER)/python -m $(PACKAGE_NAME).locales

# Tests
#
# `test` deliberately leaves out the `docker` marker. Those tests drive real
# containers -- Dex, Keycloak, and two Plone sites built from the demo image --
# and the demo image is built by `make demo-image-build`, not pulled. Running
# them from the default target means every caller needs that image, which is
# why CI gives them a job of their own that builds it first.
#
# `test-all` is the full run. Use it before pushing anything that touches the
# flow, the server layer or the demo, because `test` cannot see those.
.PHONY: test
test: $(VENV_FOLDER) ## run the tests that need no container
	@$(BIN_FOLDER)/pytest -m "not docker"

.PHONY: test-docker
test-docker: $(VENV_FOLDER) ## run the tests that drive real containers
	@$(BIN_FOLDER)/pytest -m docker

.PHONY: test-all
test-all: $(VENV_FOLDER) ## run every test, containers included
	@$(BIN_FOLDER)/pytest

.PHONY: test-coverage
test-coverage: $(VENV_FOLDER) ## run tests with coverage
	@$(BIN_FOLDER)/pytest -m "not docker" --cov=$(PACKAGE_NAME) --cov-report term-missing

# Build Docker images
.PHONY: build-image
build-image:  ## Build Docker Images
	@docker build . -t $(IMAGE_NAME) -f Dockerfile --build-arg PLONE_VERSION=$(PLONE_VERSION)

# Acceptance tests
.PHONY: demo-image-build
demo-image-build:  ## Build the federation demo image
	@docker build . -t $(IMAGE_NAME_PREFIX_WITH_SEPARATOR)demo:$(IMAGE_TAG) -f Dockerfile.demo --build-arg PLONE_VERSION=$(PLONE_VERSION)

DEMO_COMPOSE_FILE=$(BACKEND_FOLDER)/tests/federation/docker-compose.yml

.PHONY: demo-start
demo-start: ## Start the two-site federation demo
	@docker compose -f $(DEMO_COMPOSE_FILE) up -d

.PHONY: demo-stop
demo-stop: ## Stop the federation demo
	@docker compose -f $(DEMO_COMPOSE_FILE) down

.PHONY: acceptance-backend-start
acceptance-backend-start: ## Start backend acceptance server
	ZSERVER_HOST=0.0.0.0 ZSERVER_PORT=55001 LISTEN_PORT=55001 APPLY_PROFILES="$(PACKAGE_NAME):default" CONFIGURE_PACKAGES="plone.restapi,plone.volto,plone.volto.cors,$(PACKAGE_NAME)" $(BIN_FOLDER)/robot-server plone.app.robotframework.testing.VOLTO_ROBOT_TESTING

.PHONY: acceptance-image-build
acceptance-image-build:  ## Build Docker Images
	@docker build . -t $(IMAGE_NAME_PREFIX_WITH_SEPARATOR)backend-acceptance:$(IMAGE_TAG) -f Dockerfile.acceptance --build-arg PLONE_VERSION=$(PLONE_VERSION)

## Add bobtemplates features (check bobtemplates.plone's documentation to get the list of available features)
add: $(VENV_FOLDER)
	@uvx plonecli add $(filter-out $@,$(MAKECMDGOALS))
