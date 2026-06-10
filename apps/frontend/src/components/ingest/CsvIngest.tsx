import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
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
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { api } from "../../api/client";
import type { InferredColumn, UploadOut } from "../../api/types";

/** Option B — upload CSV(s), review the inferred schema, create + run the load job. */
export default function CsvIngest() {
  const nav = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [upload, setUpload] = useState<UploadOut | null>(null);
  const [cols, setCols] = useState<InferredColumn[]>([]);
  const [table, setTable] = useState("");
  const [loadMode, setLoadMode] = useState<"full" | "append">("full");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);

  async function onFile(file: File) {
    setBusy(true);
    setErr(null);
    setDone(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post<UploadOut>("/ingest/uploads", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUpload(data);
      setCols(data.schema.columns.map((c) => ({ ...c })));
      setTable(data.suggested_table);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || "upload failed");
    } finally {
      setBusy(false);
    }
  }

  function toggle(name: string) {
    setCols((cs) => cs.map((c) => (c.name === name ? { ...c, include: !c.include } : c)));
  }

  async function createAndRun() {
    if (!upload) return;
    setBusy(true);
    setErr(null);
    try {
      const selected = cols.filter((c) => c.include).map((c) => c.name);
      const body = {
        name: `load_${table}`,
        source: { kind: "csv", upload_id: upload.id, columns: selected },
        target_table: table,
        schedule: { every: "1d" },
        load_mode: loadMode,
      };
      const { data: job } = await api.post("/jobs", body);
      const { data: run } = await api.post(`/jobs/${job.id}/run`);
      setDone(`Loaded ${run.rows_written ?? "?"} rows into "${table}" (v${run.table_version ?? "?"}).`);
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

      <input
        ref={fileRef}
        type="file"
        accept=".csv,.tsv,.txt"
        hidden
        onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
      />
      <Box
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onFile(f);
        }}
        onClick={() => fileRef.current?.click()}
        sx={{
          border: "2px dashed",
          borderColor: dragOver ? "primary.main" : "divider",
          bgcolor: dragOver ? "action.hover" : "transparent",
          borderRadius: 3,
          p: 4,
          textAlign: "center",
          cursor: "pointer",
          transition: "all .15s",
        }}
      >
        <UploadFileIcon color="primary" sx={{ fontSize: 36 }} />
        <Typography sx={{ mt: 1 }}>
          {busy && !upload ? "Uploading…" : "Drop a CSV here, or click to choose"}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Delimiter, header and column types are inferred automatically (.csv / .tsv / .txt)
        </Typography>
      </Box>

      {upload && (
        <Card variant="outlined" sx={{ mt: 3 }}>
          <CardContent>
            <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
              <Chip label={upload.original_filename} />
              <Chip variant="outlined" label={`delimiter: ${JSON.stringify(upload.schema.delimiter ?? "?")}`} />
              <Chip variant="outlined" label={`header: ${String(upload.schema.has_header)}`} />
              <Chip variant="outlined" label={`~${upload.schema.row_estimate ?? "?"} rows`} />
              <Chip variant="outlined" label={`${cols.length} columns`} />
            </Stack>
            {upload.schema.warnings.map((w, i) => (
              <Alert key={i} severity="warning" sx={{ mb: 1 }}>{w}</Alert>
            ))}

            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mb: 2 }}>
              <TextField label="Target table" value={table} onChange={(e) => setTable(e.target.value)} size="small" />
              <TextField select label="Load mode" value={loadMode} onChange={(e) => setLoadMode(e.target.value as any)} size="small" sx={{ width: 160 }}>
                <MenuItem value="full">full refresh</MenuItem>
                <MenuItem value="append">append</MenuItem>
              </TextField>
            </Stack>

            <Typography variant="subtitle2" gutterBottom>Inferred schema — review before loading</Typography>
            <Box sx={{ maxHeight: 260, overflow: "auto", mb: 2 }}>
              <Table size="small" stickyHeader>
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">Use</TableCell>
                    <TableCell>Column</TableCell>
                    <TableCell>Type</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {cols.map((c) => (
                    <TableRow key={c.name} hover>
                      <TableCell padding="checkbox">
                        <Checkbox size="small" checked={c.include} onChange={() => toggle(c.name)} />
                      </TableCell>
                      <TableCell>{c.name}</TableCell>
                      <TableCell><Chip size="small" variant="outlined" label={c.type} /></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>

            {upload.schema.sample_rows.length > 0 && (
              <>
                <Typography variant="subtitle2" gutterBottom>Data preview</Typography>
                <Box sx={{ maxHeight: 220, overflow: "auto", mb: 2 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        {Object.keys(upload.schema.sample_rows[0]).map((k) => (
                          <TableCell key={k}>{k}</TableCell>
                        ))}
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {upload.schema.sample_rows.slice(0, 10).map((r, i) => (
                        <TableRow key={i}>
                          {Object.keys(upload.schema.sample_rows[0]).map((k) => (
                            <TableCell key={k}>{String(r[k] ?? "")}</TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </Box>
              </>
            )}

            <Button variant="contained" onClick={createAndRun} disabled={busy || !table}>
              {busy ? "Working…" : "Create job & load now"}
            </Button>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
