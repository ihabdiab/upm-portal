"""sqlglot-based SELECT-only validation (§11.2, §13 Phase 5 guardrails).

Used for: opt-in raw Oracle extraction SQL, and the AI `run_readonly_sql` tool.
Rejects anything that is not a single SELECT, optionally enforcing a schema allow-list.
"""

from __future__ import annotations

import sqlglot
from sqlglot import exp


class SqlValidationError(ValueError):
    pass


# Statement types that must never appear, even nested.
_FORBIDDEN = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Merge,
    exp.Command,   # catch-all for unparsed/DDL-ish commands
    exp.Grant,
)


def assert_select_only(
    sql: str,
    *,
    dialect: str = "oracle",
    allowed_schemas: set[str] | None = None,
    require_bounded: bool = False,
) -> exp.Expression:
    """Parse `sql`; raise SqlValidationError unless it is exactly one read-only SELECT.

    - single statement only
    - top node must be SELECT / WITH-wrapped SELECT
    - no forbidden statement types anywhere in the tree
    - if `allowed_schemas` given, every qualified table must live in one of them
    - if `require_bounded`, the SELECT must carry a WHERE or a row-limiting clause
    """
    try:
        statements = sqlglot.parse(sql, read=dialect)
    except Exception as e:  # noqa: BLE001 - sqlglot raises a variety of errors
        raise SqlValidationError(f"could not parse SQL: {e}") from e

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        raise SqlValidationError("exactly one statement is allowed")

    root = statements[0]

    if isinstance(root, exp.With):
        inner = root.this
    else:
        inner = root
    if not isinstance(inner, (exp.Select, exp.Union)):
        raise SqlValidationError("only SELECT statements are allowed")

    for node in root.walk():
        if isinstance(node, _FORBIDDEN):
            raise SqlValidationError(f"forbidden statement: {type(node).__name__}")

    if allowed_schemas is not None:
        allowed = {s.lower() for s in allowed_schemas}
        for table in root.find_all(exp.Table):
            db = (table.db or "").lower()
            if not db:
                raise SqlValidationError(
                    f"table {table.name!r} must be schema-qualified (allow-listed)"
                )
            if db not in allowed:
                raise SqlValidationError(f"schema {table.db!r} is not allow-listed")

    if require_bounded:
        select = inner if isinstance(inner, exp.Select) else inner.left
        has_where = select.args.get("where") is not None
        has_limit = select.args.get("limit") is not None or select.args.get("fetch") is not None
        if not (has_where or has_limit):
            raise SqlValidationError("query must be bounded (WHERE or row-limiting clause)")

    return root
