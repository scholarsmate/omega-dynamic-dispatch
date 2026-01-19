import importlib
import pkgutil

import click


def load_plugins(package: str) -> None:
    """Import all modules in a package to trigger decorator registration.

    Import errors are reported but do not abort the CLI.
    """

    pkg = importlib.import_module(package)
    for m in sorted(pkgutil.iter_modules(pkg.__path__, prefix=f"{package}."), key=lambda x: x.name):
        if m.ispkg:
            continue
        try:
            importlib.import_module(m.name)
        except Exception as e:
            click.echo(f"Warning: plugin import failed: {m.name} ({e!r})", err=True)
