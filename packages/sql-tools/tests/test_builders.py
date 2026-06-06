from upm_shared.enums import FilterOp, SourceMode
from upm_shared.jobs import JobSource
from upm_shared.query import Aggregation, Filter, QueryRequest, Sort
from upm_sql_tools import build_extract_select, build_read_select
from upm_sql_tools.identifiers import IdentifierError, validate_ident
from upm_sql_tools.validate import SqlValidationError, assert_select_only


def test_read_select_aggregation_and_filter():
    q = QueryRequest(
        table="hybrid_cs_cell",
        aggregations=[Aggregation(fn="avg", col="traffic_erl", **{"as": "traffic"})],
        groupBy=["cell_id"],
        filters=[Filter(col="region", op=FilterOp.IN, value=["North", "South"])],
        sort=[Sort(col="cell_id", dir="asc")],
        limit=100,
        page=2,
    )
    sql, params = build_read_select(q)
    assert 'avg("traffic_erl") AS "traffic"' in sql
    assert 'GROUP BY "cell_id"' in sql
    assert '"region" IN (?, ?)' in sql
    assert "LIMIT ? OFFSET ?" in sql
    # IN values, then limit, then offset = (2-1)*100
    assert params == ["North", "South", 100, 100]


def test_read_select_between_and_null():
    q = QueryRequest(
        table="t",
        columns=["a"],
        filters=[
            Filter(col="ts", op=FilterOp.BETWEEN, value=[1, 9]),
            Filter(col="x", op=FilterOp.IS_NOT_NULL),
        ],
    )
    sql, params = build_read_select(q)
    assert '"ts" BETWEEN ? AND ?' in sql
    assert '"x" IS NOT NULL' in sql
    assert params[:2] == [1, 9]


def test_identifier_rejects_injection():
    for bad in ['a"; DROP TABLE x;--', "a b", "1col", "a)"]:
        try:
            validate_ident(bad)
            raise AssertionError(f"should have rejected {bad!r}")
        except IdentifierError:
            pass


def test_oracle_extract_structured_watermark():
    src = JobSource(
        schema="SON",
        table="hybrid_cs_cell",
        mode=SourceMode.STRUCTURED,
        columns=["timestamp", "cell_id", "traffic_erl"],
    )
    sql, binds = build_extract_select(
        src, watermark_column="timestamp", watermark_value="2026-01-01", limit=1000
    )
    assert 'FROM "SON"."hybrid_cs_cell"' in sql
    assert '"timestamp" > :watermark' in sql
    assert "FETCH FIRST :row_cap ROWS ONLY" in sql
    assert binds["watermark"] == "2026-01-01"
    assert binds["row_cap"] == 1000


def test_validate_rejects_non_select():
    assert_select_only("SELECT a FROM son.t WHERE a > 1", allowed_schemas={"son"})
    for bad in [
        "DELETE FROM son.t",
        "SELECT a FROM son.t; DROP TABLE son.t",
        "UPDATE son.t SET a=1",
    ]:
        try:
            assert_select_only(bad, allowed_schemas={"son"})
            raise AssertionError(f"should have rejected: {bad}")
        except SqlValidationError:
            pass


def test_validate_enforces_schema_allowlist():
    try:
        assert_select_only("SELECT a FROM secret.t WHERE a>1", allowed_schemas={"son"})
        raise AssertionError("cross-schema should be rejected")
    except SqlValidationError:
        pass
