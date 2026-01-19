import collections.abc
import inspect
import io
import json
from enum import Enum
from typing import IO, Any, Callable, cast, get_origin, get_type_hints

import click

from .dispatch import COMMAND_META, DISPATCH
from .errors import ErrorCode
from .results import ResultObject


def _flag(name: str) -> str:
    return "--" + name.replace("_", "-")


def _is_io(ann: Any) -> bool:
    if isinstance(ann, str):
        normalized = ann.replace("typing.", "")
        if normalized == "IO" or normalized.startswith("IO["):
            return True
        return False

    origin = get_origin(ann)
    # collections.abc may not define IO in all environments; access it safely.
    abc_io = getattr(collections.abc, "IO", None)
    if ann in (IO, io.IOBase, io.TextIOBase):
        return True
    if origin is not None and (origin is IO or (abc_io is not None and origin is abc_io)):
        return True
    try:
        return isinstance(ann, type) and issubclass(ann, io.IOBase)
    except TypeError:
        return False


def _render(results: ResultObject, *, output: str, quiet: bool) -> None:
    if quiet:
        return
    if output == "json":
        click.echo(json.dumps({"ok": results.ok, "events": results.events}, default=str))
        return

    for ev in results.events:
        kind = ev.get("kind", "event")
        code = ev.get("code")
        code_num = ev.get("code_num")
        code_part = f" ({code}:{code_num})" if code or code_num is not None else ""
        msg = ev.get("message")
        details_map = ev.get("details", {})
        tail = " ".join(f"{k}={v}" for k, v in details_map.items())
        line = f"[{kind}]" + code_part + (f" {msg}" if msg else "") + (f" {tail}" if tail else "")
        click.echo(line)


def _exit_code_from_events(results: ResultObject, *, bug: bool) -> int:
    if bug:
        return 70
    if results.ok:
        return 0

    # Determine exit code from numeric ErrorCode ranges.
    # 1xxx-2xxx: input/config -> 1
    # 3xxx-5xxx: env/plugin/domain -> 2
    code_nums: list[int] = []
    for ev in results.events:
        if ev.get("kind") != "error":
            continue
        code_num = ev.get("code_num")
        if isinstance(code_num, int):
            code_nums.append(code_num)
    if not code_nums:
        return 2
    if any(1000 <= n < 3000 for n in code_nums):
        return 1
    return 2


def build_cli(prog_name: str) -> click.Group:
    @click.group(name=prog_name)
    @click.option(
        "--output",
        type=click.Choice(["text", "json"], case_sensitive=False),
        default="text",
        show_default=True,
    )
    @click.option("--quiet", is_flag=True, default=False)
    @click.pass_context
    def root(ctx: click.Context, output: str, quiet: bool) -> None:
        """Plugin-based CLI with dynamic dispatch."""
        ctx.ensure_object(dict)
        ctx.obj["output"] = output
        ctx.obj["quiet"] = quiet

    for verb, fn in sorted(DISPATCH.items()):
        meta = COMMAND_META.get(verb)
        help_text = meta.summary if meta else None
        sig = inspect.signature(fn)
        try:
            hints = get_type_hints(fn)
        except Exception:
            hints = {}
        params = list(sig.parameters.values())

        # enforce: fn(results, *, ...)
        if not params:
            raise RuntimeError(f"{verb}: missing results parameter")
        if params[0].kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            raise RuntimeError(f"{verb}: first param must be positional 'results'")
        for p in params[1:]:
            if p.kind is not inspect.Parameter.KEYWORD_ONLY:
                raise RuntimeError(f"{verb}: params after results must be keyword-only")

        def make_callback(
            fn: Callable[..., Any], sig: inspect.Signature, enum_params: dict[str, type[Enum]]
        ):
            def callback(**kwargs: Any) -> None:
                ctx = click.get_current_context()
                ctx_obj = cast(dict[str, Any], ctx.obj or {})
                output = str(ctx_obj.get("output", "text"))
                quiet = bool(ctx_obj.get("quiet", False))

                results = ResultObject()
                bug = False

                try:
                    for name, enum_cls in enum_params.items():
                        if (
                            name in kwargs
                            and kwargs[name] is not None
                            and not isinstance(kwargs[name], enum_cls)
                        ):
                            kwargs[name] = enum_cls(kwargs[name])
                    bound = sig.bind_partial(results, **kwargs)  # validates keyword binding
                    fn(*bound.args, **bound.kwargs)
                except click.ClickException:
                    # user/usage/config error -> click exits 1
                    raise
                except KeyboardInterrupt:
                    raise SystemExit(130) from None
                except Exception as e:
                    bug = True
                    results.fail(
                        "Unhandled exception",
                        code=ErrorCode.E_BUG_UNHANDLED,
                        details={"exception": repr(e)},
                    )

                _render(results, output=output, quiet=quiet)
                raise SystemExit(_exit_code_from_events(results, bug=bug))

            return callback

        enum_params: dict[str, type[Enum]] = {}
        cmd = click.Command(name=verb, callback=make_callback(fn, sig, enum_params), help=help_text)

        positional_enabled = meta.positional if meta is not None else True
        arg_params: list[click.Argument] = []
        opt_params: list[click.Option] = []

        # build parameters from keyword-only params
        for p in params[1:]:
            ann = hints.get(
                p.name,
                p.annotation if p.annotation is not inspect.Parameter.empty else str,
            )
            has_default = p.default is not inspect.Parameter.empty
            default = None if not has_default else p.default
            required = not has_default

            if positional_enabled and required and ann is not bool:
                if isinstance(ann, type) and issubclass(ann, Enum):
                    enum_params[p.name] = ann
                    arg_type: click.ParamType = click.Choice(
                        [m.value for m in ann], case_sensitive=False
                    )
                elif _is_io(ann):
                    arg_type = click.File("r")
                else:
                    arg_type = (
                        click.INT if ann is int else click.FLOAT if ann is float else click.STRING
                    )

                arg_params.append(click.Argument([p.name], type=arg_type))
                continue

            if ann is bool:
                opt = click.Option(
                    [_flag(p.name)], is_flag=True, default=bool(default) if has_default else False
                )
                opt_params.append(opt)
                continue

            if _is_io(ann):
                opt = click.Option(
                    [_flag(p.name)],
                    type=click.File("r"),
                    required=not has_default,
                    default=default,
                    metavar="PATH",
                )
                opt_params.append(opt)
                continue

            if isinstance(ann, type) and issubclass(ann, Enum):
                choices = [m.value for m in ann]
                enum_params[p.name] = ann
                opt = click.Option(
                    [_flag(p.name)],
                    type=click.Choice(choices, case_sensitive=False),
                    required=not has_default,
                    default=(default.value if has_default and default is not None else None),
                    show_default=has_default,
                )
                opt_params.append(opt)
                continue

            ctype = click.INT if ann is int else click.FLOAT if ann is float else click.STRING
            opt = click.Option(
                [_flag(p.name)],
                type=ctype,
                required=not has_default,
                default=default,
                show_default=has_default,
            )
            opt_params.append(opt)

        cmd.params.extend(arg_params + opt_params)

        root.add_command(cmd)

    return root
