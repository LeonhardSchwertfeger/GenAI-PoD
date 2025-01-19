# !make
# -*- coding: utf-8 -*-
# Copyright (C) 2024
# Benjamin Thomas Schwertfeger https://github.com/btschwertfeger
# Leonhard Thomas Schwertfeger https://github.com/LeonhardSchwertfeger
#

# Minimal Makefile for Sphinx documentation
##
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SOURCEDIR     = doc
BUILDDIR      = build

VENV := venv
PYTHON := $(VENV)/bin/python
TESTS := tests
PYTEST_OPTS := -vv

.PHONY: help
help:
	@grep "^##" Makefile | sed -e "s/##//"

## build			Builds the package
##
.PHONY: build
build:
	$(PYTHON) -m pip wheel -w dist --no-deps .

## dev			Installs the full package in edit mode
##
.PHONY: dev
dev:
	@git lfs install
	$(PYTHON) -m pip install -e ".[dev,test]"

## test			Run the unit tests
##
.PHONY: test
test:
	$(PYTHON) -m pytest $(PYTEST_OPTS) $(TESTS)

.PHONY: tests
tests: test

## wip			Run tests marked as wip
##
.PHONY: wip
wip:
	$(PYTHON) -m pytest $(PYTEST_OPTS) -m "wip" $(TESTS)

## pre-commit		Pre-Commit
##
.PHONY: pre-commit
pre-commit:
	@pre-commit run -a

## ruff			Run ruff without fix
##
.PHONY: ruff
ruff:
	ruff check --preview .

## ruff-fix 		Run ruff with fix
##
.PHONY: ruff-fix
ruff-fix:
	ruff check --fix --preview .

## clean			Clean the workspace
##
.PHONY: clean
clean:
	rm -rf .cache \
		build/ dist/ genai_pod.egg-info \
		.ipynb_checkpoints

	rm -f .coverage cmethods/_version.py

	find tests -name "__pycache__" | xargs rm -rf
	find genai_pod -name "__pycache__" | xargs rm -rf


# Build the documentation
##
html:
	$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html $(SPHINXOPTS)
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

clean-docs:
	rm -rf $(BUILDDIR)


## retest Run only the tests that failed last time
##
.PHONY: retest
retest:
	$(PYTHON) -m pytest $(PYTEST_OPTS) --lf $(TESTS)
