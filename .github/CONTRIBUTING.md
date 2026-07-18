# Contributing to flask-rls

Thanks for your interest in improving flask-rls!

## Development setup

flask-rls uses [uv](https://github.com/astral-sh/uv) for environment management.

```bash
git clone https://github.com/kdpisda/flask-rls
cd flask-rls
uv venv
uv pip install -e ".[dev]"
```

## Running the checks

```bash
.venv/bin/ruff check flask_rls tests   # lint
.venv/bin/mypy                         # type-check
.venv/bin/pytest                       # tests
```

The integration tests spin up a real PostgreSQL via
[Testcontainers](https://testcontainers.com/), so **Docker must be running**. To run only
the unit tests:

```bash
.venv/bin/pytest -m "not integration"
```

## Guidelines

- **Tests are required.** RLS is security-sensitive; behavior changes need integration
  coverage against real PostgreSQL, not just unit tests.
- **Every identifier that reaches generated DDL must be validated** (see
  `flask_rls/validation.py`). Never interpolate unvalidated input into SQL.
- Keep the public API in sync with [django-rls](https://github.com/kdpisda/django-rls)
  where it makes sense — flask-rls is its sibling.
- Run `ruff` and `mypy` before opening a PR; CI enforces both.

## Commit messages

Use conventional commits: `feat(scope): …`, `fix(scope): …`, `docs: …`, `test: …`,
`refactor: …`, `chore: …`.
