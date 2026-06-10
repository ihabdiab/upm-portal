import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
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
import { api } from "../api/client";
import type { ConnectionOut, JobDefinitionInput, SourceKind } from "../api/types";

export default function JobBuilderPage() {
  const nav = useNavigate();
  const { id } = useParams();
  const editing = !!id;

  const [kind, setKind] = useState<SourceKind>("connection");
  const [name, setName] = useState("");
  const [targetTable, setTargetTable] = useState("");
  const [loadMode, setLoadMode] = useState<"full" | "append" | "upsert">("full");
  const [watermarkCol, setWatermarkCol] = useState("");
  const [keyCols, setKeyCols] = useState("");

  // connection source
  const [connections, setConnections] = useState<ConnectionOut[]>([]);
  const [connId, setConnId] = useState<number | "">("");
  const [schema, setSchema] = useState("");
  const [table, setTable] = useState("");
  const [tables, setTables] = useState<string[]>([]);
  const [available, setAvailable] = useState<string[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // oracle/structured manual columns
  const [colsText, setColsText] = useState("");

  const [msg, setMsg] = useState<{ sev: "info" | "error" | "success"; text: string } | null>(null);
  const [preview, setPreview] = useState<Record<string, any>[] | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<ConnectionOut[]>("/connections").then(({ data }) => setConnections(data));
  }, []);

  useEffect(() => {
    if (!editing) return;
    api.get(`/jobs/${id}`).then(({ data }) => {
      const d = data.definition;
      setKind(d.source.kind);
      setName(d.name);
      setTargetTable(d.target_table);
      setLoadMode(d.load_mode);
      setWatermarkCol(d.watermark?.column ?? "");
      setKeyCols((d.key_columns ?? []).join(", "));
      setConnId(d.source.connection_id ?? "");
      setSchema(d.source.schema ?? "");
      setTable(d.source.table ?? "");
      setColsText((d.source.columns ?? []).join(", "));
      setSelected(new Set(d.source.columns ?? []));
    });
  }, [id]);

  async function loadTables(cid: number) {
    setMsg(null);
    try {
      const { data } = await api.get(`/connections/${cid}/tables`);
      setTables(data.tables ?? []);
      if (data.schemas?.length) setSchema((s) => s || data.schemas[0]);
    } catch (e: any) {
      setMsg({ sev: "error", text: e?.response?.data?.detail || "could not list tables" });
    }
  }

  async function infer() {
    if (connId === "") return;
    setBusy(true);
    setMsg(null);
    try {
      const { data } = await api.post(`/connections/${connId}/infer`, { table, schema: schema || undefined });
      const names: string[] = data.columns.map((c: any) => c.name);
      setAvailable(names);
      setSelected(new Set(names));
      if (!targetTable) setTargetTable(table.toLowerCase());
    } catch (e: any) {
      setMsg({ sev: "error", text: e?.response?.data?.detail || "inference failed" });
    } finally {
      setBusy(false);
    }
  }

  function buildBody(): JobDefinitionInput {
    const columns =
      kind === "connection"
        ? [...selected]
        : colsText.split(",").map((c) => c.trim()).filter(Boolean);
    const body: JobDefinitionInput = {
      name,
      target_table: targetTable,
      load_mode: loadMode,
      schedule: { every: "1h" },
      key_columns: keyCols.split(",").map((c) => c.trim()).filter(Boolean),
      source: {
        kind,
        mode: "structured",
        columns,
        ...(kind === "connection" ? { connection_id: Number(connId) } : {}),
        schema: schema || undefined,
        table: table || undefined,
      },
    };
    if (watermarkCol) body.watermark = { column: watermarkCol, type: "timestamp" };
    return body;
  }

  async function validate() {
    setBusy(true);
    setMsg(null);
    try {
      const { data } = await api.post("/jobs/validate", buildBody());
      setMsg({ sev: "success", text: `Valid. ${data.warnings?.join("; ") || ""}` });
    } catch (e: any) {
      setMsg({ sev: "error", text: e?.response?.data?.detail || "validation failed" });
    } finally {
      setBusy(false);
    }
  }

  async function doPreview() {
    setBusy(true);
    setMsg(null);
    try {
      const { data } = await api.post("/jobs/preview", buildBody());
      setPreview(data.rows);
    } catch (e: any) {
      setMsg({ sev: "error", text: e?.response?.data?.detail || "preview failed" });
    } finally {
      setBusy(false);
    }
  }

  async function save(run: boolean) {
    setBusy(true);
    setMsg(null);
    try {
      const body = buildBody();
      const { data: job } = editing
        ? await api.put(`/jobs/${id}`, body)
        : await api.post("/jobs", body);
      if (run) await api.post(`/jobs/${job.id}/run`);
      nav("/jobs");
    } catch (e: any) {
      setMsg({ sev: "error", text: e?.response?.data?.detail || "save failed" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>{editing ? "Edit job" : "New extraction job"}</Typography>
      {msg && <Alert severity={msg.sev} sx={{ mb: 2 }} onClose={() => setMsg(null)}>{msg.text}</Alert>}

      <Card variant="outlined">
        <CardContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={2}>
              <TextField label="Job name" value={name} onChange={(e) => setName(e.target.value)} fullWidth />
              <TextField select label="Source kind" value={kind} onChange={(e) => setKind(e.target.value as SourceKind)} sx={{ width: 220 }} disabled={editing}>
                <MenuItem value="connection">Connection (RDBMS)</MenuItem>
                <MenuItem value="oracle">Oracle / synthetic</MenuItem>
              </TextField>
            </Stack>

            {kind === "connection" && (
              <Stack direction="row" spacing={2}>
                <TextField select label="Connection" value={connId} onChange={(e) => { const v = Number(e.target.value); setConnId(v); loadTables(v); }} sx={{ width: 220 }}>
                  {connections.map((c) => <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
                </TextField>
                <TextField label="Schema" value={schema} onChange={(e) => setSchema(e.target.value)} sx={{ width: 160 }} />
                {tables.length > 0 ? (
                  <TextField select label="Table" value={table} onChange={(e) => setTable(e.target.value)} sx={{ minWidth: 220 }}>
                    {tables.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                  </TextField>
                ) : (
                  <TextField label="Table" value={table} onChange={(e) => setTable(e.target.value)} sx={{ minWidth: 220 }} />
                )}
                <Button onClick={infer} disabled={busy || connId === "" || !table}>Infer columns</Button>
              </Stack>
            )}

            {kind === "oracle" && (
              <Stack direction="row" spacing={2}>
                <TextField label="Schema" value={schema} onChange={(e) => setSchema(e.target.value)} sx={{ width: 160 }} placeholder="SON" />
                <TextField label="Table" value={table} onChange={(e) => setTable(e.target.value)} sx={{ width: 220 }} />
                <TextField label="Columns (comma-separated)" value={colsText} onChange={(e) => setColsText(e.target.value)} fullWidth />
              </Stack>
            )}

            {kind === "connection" && available.length > 0 && (
              <Box>
                <Typography variant="subtitle2">Columns ({selected.size}/{available.length})</Typography>
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
                  {available.map((c) => (
                    <Chip key={c} label={c} size="small" color={selected.has(c) ? "primary" : "default"} variant={selected.has(c) ? "filled" : "outlined"}
                      onClick={() => setSelected((s) => { const n = new Set(s); n.has(c) ? n.delete(c) : n.add(c); return n; })} />
                  ))}
                </Box>
              </Box>
            )}

            <Stack direction="row" spacing={2}>
              <TextField label="Target table" value={targetTable} onChange={(e) => setTargetTable(e.target.value)} sx={{ width: 220 }} />
              <TextField select label="Load mode" value={loadMode} onChange={(e) => setLoadMode(e.target.value as any)} sx={{ width: 160 }}>
                <MenuItem value="full">full</MenuItem>
                <MenuItem value="append">append</MenuItem>
                <MenuItem value="upsert">upsert</MenuItem>
              </TextField>
              <TextField label="Watermark column" value={watermarkCol} onChange={(e) => setWatermarkCol(e.target.value)} sx={{ width: 200 }} />
              <TextField label="Key columns (upsert)" value={keyCols} onChange={(e) => setKeyCols(e.target.value)} fullWidth />
            </Stack>

            <Stack direction="row" spacing={1}>
              <Button onClick={validate} disabled={busy}>Validate</Button>
              <Button onClick={doPreview} disabled={busy}>Preview</Button>
              <Box sx={{ flexGrow: 1 }} />
              <Button onClick={() => nav("/jobs")}>Cancel</Button>
              <Button variant="outlined" onClick={() => save(false)} disabled={busy || !name || !targetTable}>Save</Button>
              <Button variant="contained" onClick={() => save(true)} disabled={busy || !name || !targetTable}>Save & run</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>

      {preview && preview.length > 0 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>Preview ({preview.length} rows)</Typography>
            <Box sx={{ maxHeight: 280, overflow: "auto" }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>{Object.keys(preview[0]).map((k) => <TableCell key={k}>{k}</TableCell>)}</TableRow>
                </TableHead>
                <TableBody>
                  {preview.map((r, i) => (
                    <TableRow key={i}>{Object.keys(preview[0]).map((k) => <TableCell key={k}>{String(r[k] ?? "")}</TableCell>)}</TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
