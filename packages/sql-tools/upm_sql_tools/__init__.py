"""upm-sql-tools — never execute a user string. Render structured queries to
parameterized SQL, and validate any opt-in raw SQL as single-statement SELECT only.
"""

from upm_sql_tools.duckdb_builder import build_read_select
from upm_sql_tools.identifiers import IdentifierError, quote_ident, validate_ident
from upm_sql_tools.oracle_builder import build_extract_select
from upm_sql_tools.validate import SqlValidationError, assert_select_only

__all__ = [
    "IdentifierError",
    "SqlValidationError",
    "assert_select_only",
    "build_extract_select",
    "build_read_select",
    "quote_ident",
    "validate_ident",
]
