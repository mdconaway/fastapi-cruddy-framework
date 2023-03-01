#!/usr/bin/make

build:
	poetry build

formatter:
	poetry run black fastapi_cruddy_framework
	poetry run black examples
	poetry run black tests