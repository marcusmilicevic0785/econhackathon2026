.PHONY: setup verify test reproduce download notebooks

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.lock
	.venv/bin/python -m pip install --no-deps -e .

verify:
	.venv/bin/econhack verify

test:
	.venv/bin/python -m pytest -q

reproduce:
	.venv/bin/econhack run --offline

download:
	.venv/bin/econhack run

notebooks:
	.venv/bin/python scripts/build_notebooks.py --execute
