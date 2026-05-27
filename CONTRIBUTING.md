Contributing to Guardio
======================

Thanks for your interest in contributing to Guardio. This is a lightweight guide
for getting started.

Getting started
---------------

1. Fork the repository and create a feature branch from `main`.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Run tests locally:

```bash
python -m pytest
```

Code style and checks
---------------------

- We use `ruff` for linting. Run `ruff check .` and fix issues before opening a PR.
- Type checks: we run `mypy -p src.backend` in CI. Keep types updated for modified files.

Pull requests
-------------

- Open a PR targeting `main` with a clear title and description.
- Include tests for new behavior where practical.
- The CI workflow runs lint, typecheck and tests — make sure they pass locally.

Questions
---------

If you're unsure about a change or need design guidance, open an issue or a draft
PR and we can discuss the approach.
