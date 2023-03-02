#!/usr/bin/make

build:
	poetry build

publish:
	poetry build
	poetry publish

formatter:
	poetry run black fastapi_cruddy_framework
	poetry run black examples
	poetry run black tests

run-example-sqlite:
	poetry run start_sqlite