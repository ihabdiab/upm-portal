"""Identifier validation + quoting.

Values are always bound as parameters; identifiers (table/column names) cannot be
parameterized, so they are strictly validated against an allow-list pattern before
being quoted into SQL. This is the only place user-controlled names enter a statement.
"""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]{0,127}$")


class IdentifierError(ValueError):
    pass


def validate_ident(name: str, *, kind: str = "identifier") -> str:
    if not isinstance(name, str) or not _IDENT_RE.match(name):
        raise IdentifierError(f"invalid {kind}: {name!r}")
    return name


def quote_ident(name: str, *, dialect: str = "duckdb") -> str:
    """Quote a *pre-validated* identifier. Double-quote is standard for both dialects."""
    validate_ident(name)
    # No escaping needed: the allow-list forbids quotes entirely.
    return f'"{name}"'


def quote_qualified(schema: str | None, name: str, *, dialect: str = "duckdb") -> str:
    if schema:
        return f"{quote_ident(schema, dialect=dialect)}.{quote_ident(name, dialect=dialect)}"
    return quote_ident(name, dialect=dialect)
