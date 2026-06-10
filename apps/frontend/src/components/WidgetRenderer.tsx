import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { QueryResponse, Widget } from "../api/types";
import { SERIES_COLORS } from "../theme";
import FreshnessBadge from "./FreshnessBadge";

function fmtX(v: any): string {
  if (typeof v === "string" && /^\d{4}-\d{2}-\d{2}T/.test(v)) {
    const d = new Date(v);
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}h`;
  }
  return String(v);
}

function pivot(rows: any[], x: string, series: string, y: string) {
  const map = new Map<string, any>();
  const keys = new Set<string>();
  for (const r of rows) {
    const xv = String(r[x]);
    const sv = String(r[series]);
    keys.add(sv);
    if (!map.has(xv)) map.set(xv, { [x]: r[x] });
    map.get(xv)[sv] = r[y];
  }
  return { data: Array.from(map.values()), seriesKeys: Array.from(keys) };
}

/**
 * Resolve the visual mapping for a widget. Manual `viz` fields win; anything missing is
 * derived from the query itself (x = first group-by, series = second group-by,
 * y/value = first aggregation alias). This is what makes a widget render immediately
 * after picking table + aggregation + group-by, with zero extra typing.
 */
export function effectiveViz(widget: Widget): Record<string, any> {
  const viz = widget.viz || {};
  const aggs: any[] = widget.query?.aggregations ?? [];
  const groupBy: string[] = widget.query?.groupBy ?? [];
  const cols: string[] = widget.query?.columns ?? [];
  const firstAgg = aggs.find((a) => a?.as)?.as;

  return {
    ...viz,
    value: viz.value || firstAgg || "value",
    x: viz.x || groupBy[0] || cols[0],
    y: viz.y || firstAgg || cols[1],
    series: viz.series ?? (groupBy.length > 1 ? groupBy[1] : undefined),
  };
}

/** Strip incomplete editor state (e.g. an aggregation with no column yet) so the
 * preview never sends an invalid query while the user is mid-edit. */
export function sanitizeQuery(query: Record<string, any>): Record<string, any> {
  const aggs = (query.aggregations ?? []).filter(
    (a: any) => a?.fn && a?.as && (a.col || a.fn === "count"),
  );
  const sort = (query.sort ?? []).filter((s: any) => s?.col);
  return { ...query, aggregations: aggs, sort };
}

export default function WidgetRenderer({ widget, height }: { widget: Widget; height: number }) {
  const [resp, setResp] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [infoOpen, setInfoOpen] = useState(false);

  const query = sanitizeQuery({ ...widget.query, table: widget.source.table });

  useEffect(() => {
    let active = true;
    setResp(null);
    setError(null);
    api
      .post<QueryResponse>("/query", { ...query, include_sql: true })
      .then(({ data }) => active && setResp(data))
      .catch((e) => active && setError(e?.response?.data?.detail || e.message));
    return () => {
      active = false;
    };
  }, [JSON.stringify(query)]);

  const chartHeight = Math.max(120, height - 86);

  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", display: "flex", flexDirection: "column", overflow: "hidden" }}
    >
      <CardContent sx={{ pb: 1, flexGrow: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        <Stack
          direction="row"
          alignItems="center"
          spacing={0.5}
          sx={{ mb: 1, minWidth: 0 }}
        >
          <Tooltip title={widget.title} enterDelay={500}>
            <Typography
              variant="subtitle2"
              fontWeight={700}
              sx={{
                flexGrow: 1,
                minWidth: 0,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {widget.title}
            </Typography>
          </Tooltip>
          {resp && <FreshnessBadge compact dataAsOf={resp.data_as_of} stale={resp.stale} />}
          <Tooltip title="View the query behind this widget">
            <IconButton size="small" onClick={() => setInfoOpen(true)} sx={{ p: 0.25 }}>
              <InfoOutlinedIcon sx={{ fontSize: 16 }} />
            </IconButton>
          </Tooltip>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}
        {!resp && !error && (
          <Box sx={{ display: "grid", placeItems: "center", flexGrow: 1 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        {resp && !error && (
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            {resp.rows.length === 0 ? (
              <Box sx={{ display: "grid", placeItems: "center", height: chartHeight }}>
                <Typography variant="body2" color="text.secondary">
                  No data for this query.
                </Typography>
              </Box>
            ) : (
              renderBody(widget, resp.rows, chartHeight)
            )}
          </Box>
        )}
      </CardContent>

      <Dialog open={infoOpen} onClose={() => setInfoOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle sx={{ pb: 1 }}>{widget.title || "Widget query"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip size="small" label={`table: ${widget.source.table}`} />
              {resp && <Chip size="small" label={`version: v${resp.table_version}`} />}
              {resp && (
                <Chip
                  size="small"
                  color={resp.stale ? "warning" : "success"}
                  variant="outlined"
                  label={`data as of ${resp.data_as_of ? new Date(resp.data_as_of).toLocaleString() : "—"}`}
                />
              )}
              {resp && <Chip size="small" variant="outlined" label={resp.cached ? "cached" : "live"} />}
            </Stack>
            {resp?.sql && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Executed SQL (parameterized)
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    m: 0, p: 1.5, borderRadius: 2, bgcolor: "grey.900", color: "grey.100",
                    fontSize: 13, overflow: "auto", whiteSpace: "pre-wrap",
                  }}
                >
                  {resp.sql}
                </Box>
              </Box>
            )}
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Structured query
              </Typography>
              <Box
                component="pre"
                sx={{
                  m: 0, p: 1.5, borderRadius: 2, bgcolor: "grey.100",
                  fontSize: 12.5, overflow: "auto", maxHeight: 280,
                }}
              >
                {JSON.stringify(query, null, 2)}
              </Box>
            </Box>
          </Stack>
        </DialogContent>
      </Dialog>
    </Card>
  );
}

function renderBody(widget: Widget, rows: any[], h: number) {
  const viz = effectiveViz(widget);

  if (widget.type === "kpi") {
    const value = rows.length ? rows[0][viz.value] : null;
    const num = typeof value === "number" ? value : Number(value);
    const text = isNaN(num) ? "—" : num.toLocaleString(undefined, {
      maximumFractionDigits: viz.precision ?? 2,
    });
    return (
      <Box sx={{ display: "grid", placeItems: "center", height: h }}>
        <Box sx={{ textAlign: "center" }}>
          <Typography variant="h3" color="primary" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
            {text}
          </Typography>
          {viz.unit && (
            <Typography variant="body2" color="text.secondary">
              {viz.unit}
            </Typography>
          )}
        </Box>
      </Box>
    );
  }

  if (widget.type === "table") {
    const cols = rows.length ? Object.keys(rows[0]) : [];
    return (
      <Box sx={{ maxHeight: h, overflow: "auto" }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              {cols.map((c) => (
                <TableCell key={c} sx={{ fontWeight: 700 }}>{c}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.slice(0, 200).map((r, i) => (
              <TableRow key={i} hover>
                {cols.map((c) => (
                  <TableCell key={c}>{String(r[c] ?? "")}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    );
  }

  if (widget.type === "pie") {
    return (
      <ResponsiveContainer width="100%" height={h}>
        <PieChart>
          <Pie data={rows} dataKey={viz.y} nameKey={viz.x} outerRadius={Math.min(h / 2 - 14, 110)} label>
            {rows.map((_, i) => (
              <Cell key={i} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
            ))}
          </Pie>
          <ChartTooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (widget.type === "scatter") {
    return (
      <ResponsiveContainer width="100%" height={h}>
        <ScatterChart>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={viz.x} tickFormatter={fmtX} name={viz.x} />
          <YAxis dataKey={viz.y} name={viz.y} />
          <ChartTooltip />
          <Scatter data={rows} fill={SERIES_COLORS[0]} />
        </ScatterChart>
      </ResponsiveContainer>
    );
  }

  const { x, y, series } = viz;

  if ((widget.type === "line" || widget.type === "area") && series) {
    const { data, seriesKeys } = pivot(rows, x, series, y);
    const Chart = widget.type === "line" ? LineChart : AreaChart;
    return (
      <ResponsiveContainer width="100%" height={h}>
        <Chart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={x} tickFormatter={fmtX} minTickGap={24} />
          <YAxis />
          <ChartTooltip labelFormatter={fmtX} />
          <Legend />
          {seriesKeys.map((k, i) =>
            widget.type === "line" ? (
              <Line key={k} type="monotone" dataKey={k} stroke={SERIES_COLORS[i % SERIES_COLORS.length]} dot={false} />
            ) : (
              <Area key={k} type="monotone" dataKey={k} stroke={SERIES_COLORS[i % SERIES_COLORS.length]} fill={SERIES_COLORS[i % SERIES_COLORS.length]} fillOpacity={0.25} />
            ),
          )}
        </Chart>
      </ResponsiveContainer>
    );
  }

  if (widget.type === "bar") {
    return (
      <ResponsiveContainer width="100%" height={h}>
        <BarChart data={rows}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={x} tickFormatter={fmtX} minTickGap={12} />
          <YAxis />
          <ChartTooltip labelFormatter={fmtX} />
          <Bar dataKey={y} fill={SERIES_COLORS[0]} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  const Chart = widget.type === "area" ? AreaChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height={h}>
      <Chart data={rows}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={x} tickFormatter={fmtX} minTickGap={24} />
        <YAxis />
        <ChartTooltip labelFormatter={fmtX} />
        {widget.type === "area" ? (
          <Area type="monotone" dataKey={y} stroke={SERIES_COLORS[0]} fill={SERIES_COLORS[0]} fillOpacity={0.25} />
        ) : (
          <Line type="monotone" dataKey={y} stroke={SERIES_COLORS[0]} dot={false} />
        )}
      </Chart>
    </ResponsiveContainer>
  );
}
