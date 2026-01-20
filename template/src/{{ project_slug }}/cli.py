import sys

import click

from .core.click_factory import build_cli
from .core.errors import ErrorCode
from .core.plugins import load_plugins
from .core.results import ResultObject


def run(argv: list[str] | None = None) -> tuple[ResultObject, int]:
    """Programmatic entry point returning structured results and exit code."""

    argv = argv if argv is not None else sys.argv[1:]

    pkg = __package__ or __name__.split(".")[0]
    load_plugins(f"{pkg}.plugins")
    cli = build_cli(pkg, return_results=True)

    try:
        results, code = cli.main(args=argv, prog_name=pkg, standalone_mode=False)
        return results, int(code)
    except click.ClickException as exc:
        results = ResultObject(ok=False)
        results.fail(str(exc), code=ErrorCode.E_INPUT_INVALID)
        return results, 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Stable and boring by design."""

    _, code = run(argv)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
