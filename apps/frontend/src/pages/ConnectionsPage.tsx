import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import { api } from "../api/client";
import type { ConnectionIn, ConnectionKind, ConnectionOut, ConnectionTestResult } from "../api/types";

const KINDS: ConnectionKind[] = ["oracle", "postgresql", "mysql", "mssql", "generic"];
const DEFAULT_PORT: Record<string, number> = { oracle: 1521, postgresql: 5432, mysql: 3306, mssql: 1433 };

const empty: ConnectionIn = { name: "", kind: "postgresql", host: "", port: 5432, database: "", username: "", password: "" };

export default function ConnectionsPage() {
  const [conns, setConns] = useState<ConnectionOut[] | null>(null);
  const [open, setOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<ConnectionIn>(empty);
  const [test, setTest] = useState<ConnectionTestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function load() {
    api.get<ConnectionOut[]>("/connections").then(({ data }) => setConns(data));
  }
  useEffect(load, []);

  function openNew() {
    setEditId(null);
    setForm(empty);
    setTest(null);
    setErr(null);
    setOpen(true);
  }
  function openEdit(c: ConnectionOut) {
    setEditId(c.id);
    setForm({ name: c.name, kind: c.kind, host: c.host, port: c.port, database: c.database, username: c.username, password: "", sqlalchemy_url: "" });
    setTest(null);
    setErr(null);
    setOpen(true);
  }

  function setKind(kind: ConnectionKind) {
    setForm((f) => ({ ...f, kind, port: DEFAULT_PORT[kind] ?? f.port }));
  }

  async function runTest() {
    setBusy(true);
    setTest(null);
    try {
      const { data } = await api.post<ConnectionTestResult>("/connections/test", form);
      setTest(data);
    } catch (e: any) {
      setTest({ ok: false, message: e?.response?.data?.detail || "test failed" });
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      if (editId == null) await api.post("/connections", form);
      else await api.put(`/connections/${editId}`, form);
      setOpen(false);
      load();
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "save failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this connection?")) return;
    await api.delete(`/connections/${id}`);
    load();
  }

  async function testSaved(id: number) {
    const { data } = await api.post<ConnectionTestResult>(`/connections/${id}/test`);
    alert(data.ok ? `OK (${data.latency_ms ?? "?"} ms)` : `Failed: ${data.message}`);
  }

  if (!conns) return <CircularProgress />;
  const generic = form.kind === "generic";

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5">Connections</Typography>
          <Typography variant="body2" color="text.secondary">
            Saved RDBMS connections (credentials encrypted at rest). Use them as job sources.
          </Typography>
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openNew}>
          New connection
        </Button>
      </Stack>

      <Stack spacing={2}>
        {conns.map((c) => (
          <Card key={c.id} variant="outlined">
            <CardContent>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Box>
                  <Typography variant="h6">{c.name}</Typography>
                  <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
                    <Chip size="small" color="primary" variant="outlined" label={c.kind} />
                    {c.host && <Chip size="small" label={`${c.host}:${c.port ?? ""}`} />}
                    {c.database && <Chip size="small" label={c.database} />}
                    {c.username && <Chip size="small" label={c.username} />}
                  </Stack>
                </Box>
                <Stack direction="row" spacing={1}>
                  <Button size="small" onClick={() => testSaved(c.id)}>Test</Button>
                  <Button size="small" onClick={() => openEdit(c)}>Edit</Button>
                  <Button size="small" color="error" onClick={() => remove(c.id)}>Delete</Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ))}
        {conns.length === 0 && (
          <Typography color="text.secondary">No connections yet.</Typography>
        )}
      </Stack>

      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editId == null ? "New connection" : "Edit connection"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {err && <Alert severity="error">{err}</Alert>}
            <TextField label="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} fullWidth />
            <TextField select label="Type" value={form.kind} onChange={(e) => setKind(e.target.value as ConnectionKind)} fullWidth>
              {KINDS.map((k) => <MenuItem key={k} value={k}>{k}</MenuItem>)}
            </TextField>
            {generic ? (
              <TextField label="SQLAlchemy URL" value={form.sqlalchemy_url ?? ""} onChange={(e) => setForm({ ...form, sqlalchemy_url: e.target.value })} fullWidth placeholder="postgresql+psycopg://user:pass@host:5432/db" />
            ) : (
              <>
                <Stack direction="row" spacing={2}>
                  <TextField label="Host" value={form.host ?? ""} onChange={(e) => setForm({ ...form, host: e.target.value })} fullWidth />
                  <TextField label="Port" type="number" value={form.port ?? ""} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} sx={{ width: 140 }} />
                </Stack>
                <TextField label={form.kind === "oracle" ? "Service name" : "Database"} value={form.database ?? ""} onChange={(e) => setForm({ ...form, database: e.target.value })} fullWidth />
                <TextField label="Username" value={form.username ?? ""} onChange={(e) => setForm({ ...form, username: e.target.value })} fullWidth />
                <TextField label={editId == null ? "Password" : "Password (blank = keep)"} type="password" value={form.password ?? ""} onChange={(e) => setForm({ ...form, password: e.target.value })} fullWidth />
              </>
            )}
            {test && <Alert severity={test.ok ? "success" : "error"}>{test.ok ? `Connected (${test.latency_ms ?? "?"} ms)` : test.message}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={runTest} disabled={busy}>Test</Button>
          <Box sx={{ flexGrow: 1 }} />
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={save} disabled={busy || !form.name}>Save</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
