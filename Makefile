.PHONY: setup verify test reproduce download notebooks

setup:
	python3 -m venv .venv
	.venv/bin/python -m pip install -r requirements.lock
	.venv/bin/python -m pip install --no-deps -e .

verify:
	PYTHONPATH=src .venv/bin/python -m econhack.cli verify

test:
	.venv/bin/python -m pytest -q

reproduce:
	PYTHONPATH=src .venv/bin/python -m econhack.cli run --offline

download:
	PYTHONPATH=src .venv/bin/python -m econhack.cli run

notebooks:
	.venv/bin/python scripts/build_notebooks.py --execute
