from __future__ import annotations

import secrets

from .models import ErrorKind


def internal_error_code(system: str, kind: ErrorKind = ErrorKind.INTERNAL) -> str:
    """Return a short unique code for an unexpected failure incident."""

    return f"{system}-{kind.value}-{secrets.token_hex(2).upper()}"
