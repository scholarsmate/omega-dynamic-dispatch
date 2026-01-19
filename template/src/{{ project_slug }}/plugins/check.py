from ..core.dispatch import command
from ..core.errors import ErrorCode
from ..core.results import ResultObject


@command()
def check(results: ResultObject, *, required_key: str = "version") -> None:
    """Perform a simple config check.

    This is a toy example showing a domain failure reported via ResultObject.
    """

    # Pretend we looked for something and didn't find it.
    results.fail(
        f"Missing required key: {required_key}",
        code=ErrorCode.E_CONFIG_MISSING,
        details={"required_key": required_key},
    )
