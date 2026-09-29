.PHONY: install init validate test lint docs check

PY := .venv/bin/python
LISART := .venv/bin/lisart

install:          ## Crea el entorno e instala el proyecto
	uv venv --python 3.12
	uv pip install -e ".[dev]"

init:             ## Crea data/ con las tablas vacias
	$(LISART) init

validate:         ## Revisa los datos contra el esquema
	$(LISART) validate

test:             ## Corre las pruebas (sin las de pantalla, que son lentas)
	$(PY) -m pytest -q -m "not ui"

test-todo:        ## Corre TODAS las pruebas, incluidas las de la pantalla
	$(PY) -m pytest -q

ui:               ## Abre la pantalla
	$(LISART) ui

backup:           ## Respalda la capa master
	$(LISART) backup

lint:             ## Revisa estilo
	.venv/bin/ruff check src tests

docs:             ## Regenera la documentacion y el vault de Obsidian
	$(LISART) docs
	$(LISART) vault

guia:             ## Regenera docs/guia_de_uso.pdf desde el markdown
	$(LISART) guia

check: lint test  ## Lo que hay que correr antes de dar por bueno un cambio
	$(LISART) docs --check
	$(LISART) validate
	$(LISART) descuentos --revisar
	$(LISART) guia --check
