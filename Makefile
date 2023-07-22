#!/usr/bin/make

help:: ## This help dialog
	@echo
	@cat Makefile | grep -E '^[a-zA-Z\/_-]+:.*?## .*$$' | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo

install: ## Install all project dependencies and setup git hooks
	@echo "Running $@"
	pre-commit install
	poetry install

build: ## Build this project's distribution package for upload to a package mirror like PyPi
	@echo "Running $@"
	poetry build

lint: ## Lint the repository
	@echo "Running $@"
	poetry run pylint fastapi_cruddy_framework

test: ## Run pytest tests on this repository to confirm functionality and prevent regressions
	@echo "Running $@"
	poetry run coverage run --source=fastapi_cruddy_framework -m pytest tests && poetry run coverage report -m && poetry run coverage xml --fail-under 50

publish: ## Build and publish this projec't distribution package to PyPi
	@echo "Running $@"
	poetry build
	poetry publish

format: ## Format all code in this repository using the black code formatter
	@echo "Running $@"
	poetry run black fastapi_cruddy_framework
	poetry run black examples
	poetry run black tests

run-example-sqlite: ## Run the example sqlite / cruddy framework server locally to explore the framework
	@echo "Running $@"
	poetry run start_sqlite
