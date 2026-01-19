from enum import IntEnum


class ErrorCode(IntEnum):
    """Stable numeric error catalog."""

    OK = 0

    # 1xxx: input
    E_INPUT_NOT_FOUND = 1001
    E_INPUT_INVALID = 1002

    # 2xxx: config
    E_CONFIG_MISSING = 2001
    E_CONFIG_INVALID = 2002

    # 3xxx: environment
    E_ENV_PERMISSION = 3001
    E_ENV_IO = 3002

    # 4xxx: plugins
    E_PLUGIN_IMPORT = 4001
    E_PLUGIN_CONFLICT = 4002

    # 5xxx: domain
    E_DOMAIN_CONSTRAINT = 5001
    E_DOMAIN_NOT_READY = 5002

    # 9xxx: bugs
    E_BUG_UNHANDLED = 9001
    E_BUG_ASSERT = 9002
