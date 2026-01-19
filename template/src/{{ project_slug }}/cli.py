import sys

from .core.click_factory import build_cli
from .core.plugins import load_plugins


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Stable and boring by design."""
    argv = argv if argv is not None else sys.argv[1:]

    pkg = __package__ or __name__.split(".")[0]
    load_plugins(f"{pkg}.plugins")
    cli = build_cli(pkg)
    cli.main(args=argv, prog_name=pkg, standalone_mode=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
