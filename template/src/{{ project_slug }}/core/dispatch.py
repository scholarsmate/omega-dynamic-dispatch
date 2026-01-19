from dataclasses import dataclass
from typing import Any, Callable

Handler = Callable[..., Any]
DISPATCH: dict[str, Handler] = {}


@dataclass(frozen=True)
class CommandMeta:
    verb: str
    summary: str
    module: str
    positional: bool


COMMAND_META: dict[str, CommandMeta] = {}


class RegistrationError(RuntimeError):
    pass


def command(
    verb: str | None = None,
    *,
    summary: str | None = None,
    positional: bool = True,
):
    """Decorator to register a plugin handler into the dispatch registry.

    Args:
        verb: CLI verb to expose (defaults to the function name).
        summary: One-line help text (defaults to the first docstring line).
        positional: If True, required keyword-only parameters are exposed
            as positional CLI arguments. Optional parameters remain options.
            Set to False to force all parameters to be options.
    """

    def decorate(fn: Handler) -> Handler:
        v = verb or fn.__name__
        doc = (fn.__doc__ or "").strip()
        s = summary or (doc.splitlines()[0].strip() if doc else "Run command")

        if v in DISPATCH:
            prev = COMMAND_META.get(v)
            raise RegistrationError(
                f"Duplicate verb '{v}' registered by {fn.__module__}; "
                f"already registered by {prev.module if prev else 'unknown'}"
            )

        DISPATCH[v] = fn
        COMMAND_META[v] = CommandMeta(
            verb=v, summary=s, module=fn.__module__, positional=positional
        )
        return fn

    return decorate
