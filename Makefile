SHELL := /bin/bash
PYTHONPATH :=./txtool

update-pyhmy:
	cd txtool/pyhmy
	git pull https://github.com/tempoxylophone/pyhmy.git code-only
	cd ../../

install-dev:
	pipenv install --dev
	mypy --install-types

install:
	pipenv install

test:
	pytest -v -s

lint:
	mypy .
	black . --exclude '(venv|/dfk\.py/|/pyhmy\.py/)'
	pylint txtool

coverage:
	coverage run -m pytest .
	coverage html
	open htmlcov/index.html