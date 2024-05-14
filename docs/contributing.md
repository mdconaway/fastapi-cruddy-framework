## Contributing

To work on this repository, you need to take the following steps first:

- Use python 3.10+ for your local python environment. (library relies on alternative union syntax)
- Install `pre-commit` globally by using the command `pip install pre-commit` (This will be used to manage pre-commit git hooks)
- Clone this project `git clone https://github.com/mdconaway/fastapi-cruddy-framework.git` or `git clone git@github.com:mdconaway/fastapi-cruddy-framework.git`
- `cd` into this project directory.
- Run `make install` to install all dependencies and setup git pre-commit hooks!
- Use `make run-example-sqlite` to hoist an example server while operating on the framework.
- Use `make test` to confirm functionality and ensure there are no regressions after modification.
- Submit `pull` requests for new feature additions.
