import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Collapse,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import AddIcon from "@mui/icons-material/Add";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { api } from "../api/client";
import type { JobOut, RunOut } from "../api/types";

export default function JobsPage() {
  const nav = useNavigate();
  const [jobs, setJobs] = useState<JobOut[] | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const [runs, setRuns] = useState<Record<number, RunOut[]>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  function load() {
    api.get<JobOut[]>("/jobs").then(({ data }) => setJobs(data));
  }
  useEffect(load, []);

  async function loadRuns(id: number) {
    const { data } = await api.get<RunOut[]>(`/jobs/${id}/runs`);
    setRuns((r) => ({ ...r, [id]: data }));
  }

  async function runJob(id: number) {
    setBusy(id);
    setMsg(null);
    try {
      const { data } = await api.post(`/jobs/${id}/run`);
      setMsg(`Ran job ${id}: ${data.rows_written ?? "?"} rows written (v${data.table_version ?? "?"}).`);
      await loadRuns(id);
      load();
    } catch (e: any) {
      setMsg(e?.response?.data?.detail || "Run failed");
    } finally {
      setBusy(null);
    }
  }

  async function remove(id: number) {
    if (!confirm("Delete this job? (the loaded table is left intact)")) return;
    await api.delete(`/jobs/${id}`);
    load();
  }

  function toggle(id: number) {
    setOpen((o) => (o === id ? null : id));
    if (!runs[id]) loadRuns(id);
  }

  if (!jobs) return <CircularProgress />;

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5">Extraction Jobs</Typography>
          <Typography variant="body2" color="text.secondary">
            Each job extracts a delta to the Parquet landing zone, then the Gateway loads it into
            DuckDB. Config is data — no deploys.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button startIcon={<UploadFileIcon />} onClick={() => nav("/ingest")}>Ingest CSV</Button>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => nav("/jobs/new")}>New job</Button>
        </Stack>
      </Stack>

      {msg && (
        <Alert severity="info" sx={{ mb: 2 }} onClose={() => setMsg(null)}>
          {msg}
        </Alert>
      )}
      <Stack spacing={2}>
        {jobs.map((j) => {
          const def = j.definition as any;
          const src = def.source ?? {};
          const sourceLabel =
            src.kind === "csv" ? "csv upload"
            : src.kind === "connection" ? `connection #${src.connection_id ?? "?"}`
            : `${src.schema ?? "?"}.${src.table ?? "?"}`;
          return (
            <Card key={j.id} variant="outlined">
              <CardContent>
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography variant="h6">{def.name}</Typography>
                    <Stack direction="row" spacing={1} sx={{ mt: 0.5 }} flexWrap="wrap">
                      <Chip size="small" color="secondary" variant="outlined" label={src.kind ?? "oracle"} />
                      <Chip size="small" label={sourceLabel} />
                      <Chip size="small" label={`→ ${def.target_table}`} />
                      <Chip size="small" color="primary" label={def.load_mode} variant="outlined" />
                      <Chip size="small" label={`every ${def.schedule?.every ?? def.schedule?.cron}`} variant="outlined" />
                      <Chip
                        size="small"
                        label={j.is_enabled ? "enabled" : "disabled"}
                        color={j.is_enabled ? "success" : "default"}
                        variant="outlined"
                      />
                    </Stack>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" onClick={() => toggle(j.id)}>
                      {open === j.id ? "Hide runs" : "Runs"}
                    </Button>
                    <Button size="small" onClick={() => nav(`/jobs/${j.id}/edit`)}>Edit</Button>
                    <Button size="small" color="error" onClick={() => remove(j.id)}>Delete</Button>
                    <Button
                      size="small"
                      variant="contained"
                      startIcon={<PlayArrowIcon />}
                      disabled={busy === j.id}
                      onClick={() => runJob(j.id)}
                    >
                      {busy === j.id ? "Running…" : "Run now"}
                    </Button>
                  </Stack>
                </Stack>

                <Collapse in={open === j.id} sx={{ mt: 2 }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Run</TableCell>
                        <TableCell>Status</TableCell>
                        <TableCell align="right">Read</TableCell>
                        <TableCell align="right">Written</TableCell>
                        <TableCell>Watermark</TableCell>
                        <TableCell>Started</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {(runs[j.id] ?? []).map((r) => (
                        <TableRow key={r.id}>
                          <TableCell>#{r.id}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={r.status}
                              color={
                                r.status === "success" ? "success" : r.status === "failed" ? "error" : "warning"
                              }
                            />
                          </TableCell>
                          <TableCell align="right">{r.rows_read}</TableCell>
                          <TableCell align="right">{r.rows_written}</TableCell>
                          <TableCell>{r.watermark_after ?? "—"}</TableCell>
                          <TableCell>{r.started_at ? new Date(r.started_at).toLocaleString() : "—"}</TableCell>
                        </TableRow>
                      ))}
                      {(runs[j.id] ?? []).length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6}>
                            <Typography variant="body2" color="text.secondary">No runs yet.</Typography>
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </Collapse>
              </CardContent>
            </Card>
          );
        })}
      </Stack>
    </Box>
  );
}
