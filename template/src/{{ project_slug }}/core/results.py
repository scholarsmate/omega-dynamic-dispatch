from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, cast

from .errors import ErrorCode


@dataclass
class ResultObject:
    ok: bool = True
    events: List[Dict[str, Any]] = field(default_factory=lambda: cast(List[Dict[str, Any]], []))

    def add_event(
        self,
        kind: str,
        *,
        message: str | None = None,
        code: ErrorCode | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.events.append(
            {
                "kind": kind,
                "message": message,
                "code": code.name if code is not None else None,
                "code_num": int(code) if code is not None else None,
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "details": details or {},
            }
        )

    def fail(self, message: str, *, code: ErrorCode, details: dict[str, Any] | None = None) -> None:
        self.ok = False
        self.add_event("error", message=message, code=code, details=details)
