import { useEffect, useState } from "react";
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
import { api } from "../../api/client";
import type { ConnectionOut } from "../../api/types";

/** Option A — pick a saved connection, choose a table, infer its schema, preview, load. */
export default function ConnectionIngest() {
  const nav = useNavigate();
  const [connections, setConnections] = useState<ConnectionOut[]>([]);
  const [connId, setConnId] = useState<number | "">("");
  const [schema, setSchema] = useState("");
  const [schemas, setSchemas] = useState<string[]>([]);
  const [table, setTable] = useState("");
  const [tables, setTables] = useState<string[]>([]);
  const [available, setAvailable] = useState<{ name: string; type: string }[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [sample, setSample] = useState<Record<string, any>[]>([]);
  const [target, setTarget] = useState("");
  const [loadMode, setLoadMode] = useState<"full" | "append">("full");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    api.get<ConnectionOut[]>("/connections").then(({ data }) => setConnections(data));
  }, []);

  async function pickConnection(cid: number) {
    setConnId(cid);
    setErr(null);
    setTables([]);
    setAvailable([]);
    try {
      const { data } = await api.get(`/connections/${cid}/tables`, { params: schema ? { schema } : {} });
      setTables(data.tables ?? []);
      setSchemas(data.schemas ?? []);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "could not list tables on this connection");
    }
  }

  async function infer() {
    if (connId === "" || !table) return;
    setBusy(true);
    setErr(null);
    try {
      const { data } = await api.post(`/connections/${connId}/infer`, {
        table,
        schema: schema || undefined,
      });
      setAvailable(data.columns.map((c: any) => ({ name: c.name, type: c.type })));
      setSelected(new Set(data.columns.map((c: any) => c.name)));
      setSample(data.sample_rows ?? []);
      if (!target) setTarget(table.toLowerCase());
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "schema inference failed");
    } finally {
      setBusy(false);
    }
  }

  async function createAndRun() {
    setBusy(true);
    setErr(null);
    try {
      const body = {
        name: `load_${target}`,
        source: {
          kind: "connection",
          connection_id: Number(connId),
          mode: "structured",
          schema: schema || undefined,
          table,
          columns: [...selected],
        },
        target_table: target,
        schedule: { every: "1h" },
        load_mode: loadMode,
      };
      const { data: job } = await api.post("/jobs", body);
      const { data: run } = await api.post(`/jobs/${job.id}/run`);
      setDone(`Loaded ${run.rows_written ?? "?"} rows into "${target}".`);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "job creation/run failed");
    } finally {
      setBusy(false);
    }
  }

  if (connections.length === 0) {
    return (
      <Alert
        severity="info"
        action={<Button color="inherit" size="small" onClick={() => nav("/connections")}>Connections</Button>}
      >
        No saved connections yet. Create one in the Connections page first (Oracle, PostgreSQL,
        MySQL, MSSQL, or a generic SQLAlchemy URL).
      </Alert>
    );
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

      <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
        <TextField
          select
          label="Connection"
          value={connId}
          onChange={(e) => pickConnection(Number(e.target.value))}
          sx={{ minWidth: 220 }}
          size="small"
        >
          {connections.map((c) => (
            <MenuItem key={c.id} value={c.id}>{c.name} ({c.kind})</MenuItem>
          ))}
        </TextField>
        {schemas.length > 0 ? (
          <TextField select label="Schema" value={schema} size="small" sx={{ minWidth: 160 }}
            onChange={(e) => { setSchema(e.target.value); if (connId !== "") pickConnection(Number(connId)); }}>
            <MenuItem value="">(default)</MenuItem>
            {schemas.map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </TextField>
        ) : (
          <TextField label="Schema (optional)" value={schema} onChange={(e) => setSchema(e.target.value)} size="small" sx={{ minWidth: 160 }} />
        )}
        {tables.length > 0 ? (
          <TextField select label="Source table" value={table} onChange={(e) => setTable(e.target.value)} size="small" sx={{ minWidth: 220 }}>
            {tables.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
          </TextField>
        ) : (
          <TextField label="Source table" value={table} onChange={(e) => setTable(e.target.value)} size="small" sx={{ minWidth: 220 }} />
        )}
        <Button onClick={infer} disabled={busy || connId === "" || !table} variant="outlined">
          Infer schema
        </Button>
      </Stack>

      {available.length > 0 && (
        <>
          <Typography variant="subtitle2" gutterBottom>
            Columns ({selected.size}/{available.length}) — click to include/exclude
          </Typography>
          <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mb: 2 }}>
            {available.map((c) => (
              <Chip
                key={c.name}
                label={`${c.name} · ${c.type}`}
                size="small"
                color={selected.has(c.name) ? "primary" : "default"}
                variant={selected.has(c.name) ? "filled" : "outlined"}
                onClick={() =>
                  setSelected((s) => {
                    const n = new Set(s);
                    n.has(c.name) ? n.delete(c.name) : n.add(c.name);
                    return n;
                  })
                }
              />
            ))}
          </Box>

          {sample.length > 0 && (
            <>
              <Typography variant="subtitle2" gutterBottom>Data preview</Typography>
              <Box sx={{ maxHeight: 220, overflow: "auto", mb: 2 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      {Object.keys(sample[0]).map((k) => <TableCell key={k}>{k}</TableCell>)}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {sample.slice(0, 10).map((r, i) => (
                      <TableRow key={i}>
                        {Object.keys(sample[0]).map((k) => (
                          <TableCell key={k}>{String(r[k] ?? "")}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </>
          )}

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField label="Target table" value={target} onChange={(e) => setTarget(e.target.value)} size="small" />
            <TextField select label="Load mode" value={loadMode} onChange={(e) => setLoadMode(e.target.value as any)} size="small" sx={{ width: 160 }}>
              <MenuItem value="full">full refresh</MenuItem>
              <MenuItem value="append">append</MenuItem>
            </TextField>
            <Button variant="contained" onClick={createAndRun} disabled={busy || !target || selected.size === 0}>
              {busy ? "Working…" : "Create job & load now"}
            </Button>
          </Stack>
        </>
      )}
    </Box>
  );
}
