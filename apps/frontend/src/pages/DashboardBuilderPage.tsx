import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DeleteIcon from "@mui/icons-material/Delete";
import AddIcon from "@mui/icons-material/Add";
import { api } from "../api/client";
import type { ProjectOut, TableSummary, Widget } from "../api/types";
import WidgetRenderer from "../components/WidgetRenderer";

const TYPES = ["line", "bar", "area", "pie", "scatter", "kpi", "table"];
const AGG_FNS = ["sum", "avg", "min", "max", "count", "count_distinct", "median", "stddev"];

function blankWidget(): Widget {
  return {
    id: `w${Math.random().toString(36).slice(2, 8)}`,
    type: "bar",
    title: "New widget",
    source: { table: "" },
    query: { aggregations: [], groupBy: [], sort: [], limit: 1000 },
    viz: {},
    grid: { x: 0, y: 0, w: 6, h: 5 },
  } as Widget;
}

export default function DashboardBuilderPage() {
  const nav = useNavigate();
  const { id } = useParams();
  const editing = !!id;

  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [projectId, setProjectId] = useState<number | "">("");
  const [name, setName] = useState("New dashboard");
  const [widgets, setWidgets] = useState<Widget[]>([blankWidget()]);
  const [tables, setTables] = useState<string[]>([]);
  const [colsByTable, setColsByTable] = useState<Record<string, string[]>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<ProjectOut[]>("/projects").then(({ data }) => setProjects(data));
    api.get<TableSummary[]>("/catalog/tables").then(({ data }) => setTables(data.map((t) => t.table_name)));
  }, []);

  useEffect(() => {
    if (!editing) return;
    api.get(`/dashboards/${id}`).then(({ data }) => {
      setName(data.name);
      setProjectId(data.project_id);
      setWidgets(data.definition.widgets ?? []);
    });
  }, [id]);

  async function ensureCols(table: string) {
    if (!table || colsByTable[table]) return;
    const { data } = await api.get(`/catalog/tables/${table}`);
    setColsByTable((m) => ({ ...m, [table]: data.columns.map((c: any) => c.name) }));
  }

  function update(i: number, patch: Partial<Widget>) {
    setWidgets((ws) => ws.map((w, j) => (j === i ? { ...w, ...patch } : w)));
  }
  function updateQuery(i: number, patch: Record<string, any>) {
    setWidgets((ws) => ws.map((w, j) => (j === i ? { ...w, query: { ...w.query, ...patch } } : w)));
  }
  function updateViz(i: number, patch: Record<string, any>) {
    setWidgets((ws) => ws.map((w, j) => (j === i ? { ...w, viz: { ...w.viz, ...patch } } : w)));
  }

  async function save() {
    setBusy(true);
    setErr(null);
    try {
      const definition = { version: 1, layout: { cols: 12, rowHeight: 40 }, widgets };
      if (editing) {
        await api.put(`/dashboards/${id}`, { name, definition });
      } else {
        if (projectId === "") throw new Error("pick a project");
        await api.post(`/projects/${projectId}/dashboards`, { name, definition });
      }
      nav("/dashboards");
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e.message || "save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h5">{editing ? "Edit dashboard" : "New dashboard"}</Typography>
        <Stack direction="row" spacing={1}>
          <Button onClick={() => nav("/dashboards")}>Cancel</Button>
          <Button variant="contained" onClick={save} disabled={busy || !name}>Save</Button>
        </Stack>
      </Stack>
      {err && <Alert severity="error" sx={{ mb: 2 }}>{err}</Alert>}

      <Stack direction="row" spacing={2} sx={{ mb: 3 }}>
        <TextField label="Dashboard name" value={name} onChange={(e) => setName(e.target.value)} sx={{ width: 320 }} />
        {!editing && (
          <TextField select label="Project" value={projectId} onChange={(e) => setProjectId(Number(e.target.value))} sx={{ width: 240 }}>
            {projects.map((p) => <MenuItem key={p.id} value={p.id}>{p.name}</MenuItem>)}
          </TextField>
        )}
      </Stack>

      {widgets.map((w, i) => {
        const cols = colsByTable[w.source.table] ?? [];
        const aggs = (w.query.aggregations ?? []) as any[];
        const groupBy = (w.query.groupBy ?? []) as string[];
        return (
          <Accordion key={w.id} defaultExpanded={widgets.length <= 2}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Stack direction="row" spacing={1} alignItems="center" sx={{ width: "100%" }}>
                <Chip size="small" label={w.type} color="primary" variant="outlined" />
                <Typography>{w.title || "(untitled)"}</Typography>
                <Box sx={{ flexGrow: 1 }} />
                <Chip size="small" label={w.source.table || "no table"} />
              </Stack>
            </AccordionSummary>
            <AccordionDetails>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <Box sx={{ flex: 1 }}>
                  <Stack spacing={2}>
                    <Stack direction="row" spacing={2}>
                      <TextField select label="Type" value={w.type} onChange={(e) => update(i, { type: e.target.value as any })} sx={{ width: 130 }}>
                        {TYPES.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                      </TextField>
                      <TextField label="Title" value={w.title} onChange={(e) => update(i, { title: e.target.value })} fullWidth />
                    </Stack>

                    <TextField select label="Table" value={w.source.table}
                      onChange={(e) => { update(i, { source: { table: e.target.value } }); ensureCols(e.target.value); }}>
                      {tables.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
                    </TextField>

                    <Divider textAlign="left"><Typography variant="caption">Aggregations</Typography></Divider>
                    {aggs.map((a, ai) => (
                      <Stack key={ai} direction="row" spacing={1} alignItems="center">
                        <TextField select label="fn" value={a.fn} sx={{ width: 130 }}
                          onChange={(e) => { const na = [...aggs]; na[ai] = { ...a, fn: e.target.value }; updateQuery(i, { aggregations: na }); }}>
                          {AGG_FNS.map((f) => <MenuItem key={f} value={f}>{f}</MenuItem>)}
                        </TextField>
                        <TextField select label="column" value={a.col ?? ""} sx={{ minWidth: 160 }}
                          onChange={(e) => { const na = [...aggs]; na[ai] = { ...a, col: e.target.value }; updateQuery(i, { aggregations: na }); }}>
                          <MenuItem value="">(none / count*)</MenuItem>
                          {cols.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                        </TextField>
                        <TextField label="as" value={a.as ?? ""} sx={{ width: 120 }}
                          onChange={(e) => { const na = [...aggs]; na[ai] = { ...a, as: e.target.value }; updateQuery(i, { aggregations: na }); }} />
                        <IconButton size="small" onClick={() => updateQuery(i, { aggregations: aggs.filter((_, k) => k !== ai) })}><DeleteIcon fontSize="small" /></IconButton>
                      </Stack>
                    ))}
                    <Button size="small" startIcon={<AddIcon />} onClick={() => updateQuery(i, { aggregations: [...aggs, { fn: "sum", col: "", as: `m${aggs.length + 1}` }] })}>
                      Add aggregation
                    </Button>

                    <TextField select label="Group by" SelectProps={{ multiple: true }} value={groupBy}
                      onChange={(e) => updateQuery(i, { groupBy: e.target.value as any })}>
                      {cols.map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                    </TextField>

                    <Stack direction="row" spacing={2}>
                      <TextField label="Limit" type="number" value={w.query.limit ?? 1000}
                        onChange={(e) => updateQuery(i, { limit: Number(e.target.value) })} sx={{ width: 120 }} />
                      <TextField select label="Sort col" value={w.query.sort?.[0]?.col ?? ""} sx={{ minWidth: 160 }}
                        onChange={(e) => updateQuery(i, { sort: e.target.value ? [{ col: e.target.value, dir: w.query.sort?.[0]?.dir ?? "asc" }] : [] })}>
                        <MenuItem value="">(none)</MenuItem>
                        {[...cols, ...aggs.map((a) => a.as)].map((c) => <MenuItem key={c} value={c}>{c}</MenuItem>)}
                      </TextField>
                      <TextField select label="Dir" value={w.query.sort?.[0]?.dir ?? "asc"} sx={{ width: 110 }} disabled={!w.query.sort?.[0]}
                        onChange={(e) => updateQuery(i, { sort: [{ col: w.query.sort[0].col, dir: e.target.value }] })}>
                        <MenuItem value="asc">asc</MenuItem>
                        <MenuItem value="desc">desc</MenuItem>
                      </TextField>
                    </Stack>

                    <Divider textAlign="left"><Typography variant="caption">Visualization</Typography></Divider>
                    {w.type === "kpi" ? (
                      <Stack direction="row" spacing={2}>
                        <TextField label="Value field" value={w.viz.value ?? ""} onChange={(e) => updateViz(i, { value: e.target.value })} sx={{ width: 160 }} />
                        <TextField label="Unit" value={w.viz.unit ?? ""} onChange={(e) => updateViz(i, { unit: e.target.value })} sx={{ width: 120 }} />
                        <TextField label="Precision" type="number" value={w.viz.precision ?? 2} onChange={(e) => updateViz(i, { precision: Number(e.target.value) })} sx={{ width: 120 }} />
                      </Stack>
                    ) : w.type !== "table" ? (
                      <Stack direction="row" spacing={2}>
                        <TextField label="X / name" value={w.viz.x ?? ""} onChange={(e) => updateViz(i, { x: e.target.value })} sx={{ width: 160 }} />
                        <TextField label="Y / value" value={w.viz.y ?? ""} onChange={(e) => updateViz(i, { y: e.target.value })} sx={{ width: 160 }} />
                        {(w.type === "line" || w.type === "area") && (
                          <TextField label="Series (optional)" value={w.viz.series ?? ""} onChange={(e) => updateViz(i, { series: e.target.value })} sx={{ width: 160 }} />
                        )}
                      </Stack>
                    ) : (
                      <Typography variant="caption" color="text.secondary">Table shows the query result columns directly.</Typography>
                    )}

                    <Divider textAlign="left"><Typography variant="caption">Layout</Typography></Divider>
                    <Stack direction="row" spacing={2}>
                      {(["x", "y", "w", "h"] as const).map((k) => (
                        <TextField key={k} label={k} type="number" value={(w.grid as any)[k]} sx={{ width: 80 }}
                          onChange={(e) => update(i, { grid: { ...w.grid, [k]: Number(e.target.value) } })} />
                      ))}
                      <Box sx={{ flexGrow: 1 }} />
                      <Button color="error" startIcon={<DeleteIcon />} onClick={() => setWidgets((ws) => ws.filter((_, j) => j !== i))}>
                        Remove widget
                      </Button>
                    </Stack>
                  </Stack>
                </Box>

                <Box sx={{ width: { xs: "100%", md: 380 }, minHeight: 260 }}>
                  <Typography variant="caption" color="text.secondary">Live preview</Typography>
                  {w.source.table ? (
                    <Box sx={{ height: 260 }}>
                      <WidgetRenderer widget={w} height={260} />
                    </Box>
                  ) : (
                    <Card variant="outlined" sx={{ height: 260, display: "grid", placeItems: "center" }}>
                      <Typography variant="body2" color="text.secondary">Pick a table to preview</Typography>
                    </Card>
                  )}
                </Box>
              </Stack>
            </AccordionDetails>
          </Accordion>
        );
      })}

      <Button sx={{ mt: 2 }} startIcon={<AddIcon />} onClick={() => setWidgets((ws) => [...ws, blankWidget()])}>
        Add widget
      </Button>
    </Box>
  );
}
