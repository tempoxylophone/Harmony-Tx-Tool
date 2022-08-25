SHELL := /bin/bash
PYTHONPATH :=./txtool

install-dev:
	pipenv install --dev
	mypy --install-types

install:
	pipenv install

requirements:
	pipenv lock -r > requirements.txt
	pipenv lock -r --dev > requirements-dev.txt

test:
	pytest -v -s -rx --random-order -m "not slow"

lint:
	mypy .
	black . --exclude '(venv|/dfk\.py/|/pyhmy\.py/)'
	pylint txtool

coverage:
	coverage run -m pytest .
	coverage html
	open htmlcov/index.html