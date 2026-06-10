import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { api } from "../../api/client";
import type { TableSummary } from "../../api/types";

/** Option C — run a SELECT over already-loaded DuckDB tables; preview the result; save it
 * as a transform job (the Gateway executes the SQL — SELECT-only, validated server-side). */
export default function SqlIngest() {
  const nav = useNavigate();
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [sql, setSql] = useState("");
  const [valid, setValid] = useState<null | { ok: boolean; message: string }>(null);
  const [preview, setPreview] = useState<{ columns: string[]; rows: Record<string, any>[] } | null>(null);
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    api.get<TableSummary[]>("/catalog/tables").then(({ data }) => setTables(data));
  }, []);

  function insertTable(name: string) {
    const el = editorRef.current;
    const quoted = `"${name}"`;
    if (!el) {
      setSql((s) => s + quoted);
      return;
    }
    const start = el.selectionStart ?? sql.length;
    const end = el.selectionEnd ?? sql.length;
    const next = sql.slice(0, start) + quoted + sql.slice(end);
    setSql(next);
    requestAnimationFrame(() => {
      el.focus();
      el.selectionStart = el.selectionEnd = start + quoted.length;
    });
  }

  async function validate() {
    setValid(null);
    setErr(null);
    try {
      await api.post("/duckdb/validate", { sql });
      setValid({ ok: true, message: "Valid single-statement SELECT." });
    } catch (e: any) {
      setValid({ ok: false, message: e?.response?.data?.detail || "invalid SQL" });
    }
  }

  async function runPreview() {
    setBusy(true);
    setErr(null);
    setPreview(null);
    try {
      const { data } = await api.post("/duckdb/preview", { sql });
      setPreview(data);
      setValid({ ok: true, message: "Valid single-statement SELECT." });
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "query failed");
    } finally {
      setBusy(false);
    }
  }

  async function createAndRun() {
    setBusy(true);
    setErr(null);
    try {
      const body = {
        name: `derive_${target}`,
        source: { kind: "duckdb_query", duckdb_sql: sql },
        target_table: target,
        schedule: { every: "1d" },
        load_mode: "full",
      };
      const { data: job } = await api.post("/jobs", body);
      const { data: run } = await api.post(`/jobs/${job.id}/run`);
      setDone(`Materialized ${run.row_count ?? "?"} rows into "${target}".`);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "job creation/run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      {err && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErr(null)}>{err}</Alert>}
      {done && (
        <Alert
          severity="success"
          sx={{ mb: 2 }}
          action={<Button color="inherit" size="small" onClick={() => nav("/catalog")}>View in catalog</Button>}
        >
          {done}
        </Alert>
      )}

      <Typography variant="subtitle2" gutterBottom>
        Available tables — click to insert at the cursor
      </Typography>
      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 1.5 }}>
        {tables.map((t) => (
          <Chip
            key={t.table_name}
            size="small"
            variant="outlined"
            label={`${t.table_name} (${t.row_count.toLocaleString()})`}
            onClick={() => insertTable(t.table_name)}
          />
        ))}
        {tables.length === 0 && (
          <Typography variant="caption" color="text.secondary">
            No tables loaded yet — ingest something first.
          </Typography>
        )}
      </Box>

      <TextField
        inputRef={editorRef}
        value={sql}
        onChange={(e) => { setSql(e.target.value); setValid(null); }}
        multiline
        minRows={6}
        maxRows={16}
        fullWidth
        placeholder={'SELECT "REGION", sum("TRAFFIC_3G") AS traffic\nFROM "cs_cell"\nGROUP BY "REGION"'}
        InputProps={{
          sx: { fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace", fontSize: 13.5 },
        }}
      />
      {valid && (
        <Alert severity={valid.ok ? "success" : "error"} sx={{ mt: 1 }}>
          {valid.message}
        </Alert>
      )}

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} sx={{ mt: 2 }} alignItems={{ sm: "center" }}>
        <Button onClick={validate} disabled={!sql.trim()}>Validate</Button>
        <Button startIcon={<PlayArrowIcon />} variant="outlined" onClick={runPreview} disabled={busy || !sql.trim()}>
          {busy ? "Running…" : "Run preview"}
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <TextField label="Target table" value={target} onChange={(e) => setTarget(e.target.value)} size="small" />
        <Button variant="contained" onClick={createAndRun} disabled={busy || !target || !sql.trim()}>
          Save as job & materialize
        </Button>
      </Stack>

      {preview && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Preview ({preview.rows.length} rows{preview.rows.length >= 200 ? ", capped" : ""})
          </Typography>
          <Box sx={{ maxHeight: 320, overflow: "auto" }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {preview.columns.map((c) => <TableCell key={c} sx={{ fontWeight: 700 }}>{c}</TableCell>)}
                </TableRow>
              </TableHead>
              <TableBody>
                {preview.rows.map((r, i) => (
                  <TableRow key={i} hover>
                    {preview.columns.map((c) => (
                      <TableCell key={c}>{String(r[c] ?? "")}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      )}
    </Box>
  );
}
