# Omega Dynamic Dispatch (ODD)

[![CI](https://github.com/scholarsmate/omega-dynamic-dispatch/actions/workflows/ci.yml/badge.svg)](https://github.com/scholarsmate/omega-dynamic-dispatch/actions/workflows/ci.yml)

Omega Dynamic Dispatch (ODD) is a Copier template that generates a **plugin-based Click CLI** with dict-backed dynamic dispatch.

## Quickstart

```bash
pipx install copier
copier copy . ./mytool
```

Then:

```bash
cd mytool
python -m pip install -e .
mytool --help
```

## Using the template

Create a new project from the ODD template:

```bash
copier copy https://github.com/scholarsmate/omega-dynamic-dispatch ./mytool
```

You can also use a local checkout while iterating:

```bash
copier copy . ./mytool
```

Copier will prompt for answers (project name, slug, Python version, etc.) and render a
ready-to-run CLI in your destination folder.

## Updating an existing project

If the ODD template changes, you can update an existing project using Copier:

```bash
cd ./mytool
copier update
```

If you want to update from a specific ODD tag or branch:

```bash
copier update --vcs-ref v0.2.0
```

Copier will merge ODD template changes into your project and prompt you to resolve any
conflicts.

## Project tooling

This repository includes a top-level [pyproject.toml](pyproject.toml) for development tooling
configuration (ruff/pytest) and metadata for the template project itself.

## Versioning

This project follows Semantic Versioning (SemVer). Release tags use the
`vX.Y.Z` format and changes are tracked in the changelog.

Versions are derived from git tags using setuptools-scm (single source of truth).

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Testing

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## License

Apache 2.0. See [LICENSE](LICENSE).
