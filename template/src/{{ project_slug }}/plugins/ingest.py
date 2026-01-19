from enum import Enum
from typing import IO

from ..core.dispatch import command
from ..core.errors import ErrorCode
from ..core.results import ResultObject


class DataType(str, Enum):
    USERS = "users"
    ORDERS = "orders"
    EVENTS = "events"


@command()
def ingest(results: ResultObject, *, data_type: DataType, data_file: IO[str]) -> None:
    """Ingest a data file.

    Args:
        data_type: Category of the file.
        data_file: Input file (opened by Click).
    """

    text = data_file.read()
    results.add_event(
        "ingest",
        message="Ingest completed",
        code=ErrorCode.OK,
        details={"data_type": data_type.value, "bytes": len(text.encode("utf-8"))},
    )
