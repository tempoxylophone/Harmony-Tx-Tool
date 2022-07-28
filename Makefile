SHELL := /bin/bash

update-pyhmy:
	cd .txtool/pyhmy
	git pull
	cd ../../

install-dev:
	pipenv install --dev
	mypy --install-types

install:
	pipenv install

test:
	PYTHONPATH=./txtool pytest

lint:
	PYTHONPATH=./txtool mypy .