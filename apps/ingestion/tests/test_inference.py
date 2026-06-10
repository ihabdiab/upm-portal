from upm_ingestion.inference import infer_csv


def _write(path, text):
    path.write_text(text, encoding="utf-8")
    return str(path)


def test_infer_csv_comma(tmp_path):
    p = _write(
        tmp_path / "kpi.csv",
        "cell_id,traffic,region\nC1,10.5,North\nC2,20.0,South\nC3,,East\n",
    )
    schema = infer_csv(p)
    names = {c.name for c in schema.columns}
    assert names == {"cell_id", "traffic", "region"}
    types = {c.name: c.type for c in schema.columns}
    assert "VARCHAR" in types["cell_id"]
    assert types["traffic"] in ("DOUBLE", "FLOAT")
    assert schema.row_estimate == 3
    assert schema.delimiter == ","
    assert len(schema.sample_rows) == 3


def test_infer_csv_semicolon(tmp_path):
    p = _write(tmp_path / "s.csv", "a;b\n1;x\n2;y\n")
    schema = infer_csv(p)
    assert schema.delimiter == ";"
    assert {c.name for c in schema.columns} == {"a", "b"}
