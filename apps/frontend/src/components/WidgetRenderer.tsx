import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
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
  Tooltip,
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

export default function WidgetRenderer({ widget, height }: { widget: Widget; height: number }) {
  const [resp, setResp] = useState<QueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setResp(null);
    setError(null);
    api
      .post<QueryResponse>("/query", { ...widget.query, table: widget.source.table })
      .then(({ data }) => active && setResp(data))
      .catch((e) => active && setError(e?.response?.data?.detail || e.message))
      .finally(() => {});
    return () => {
      active = false;
    };
  }, [JSON.stringify(widget.query), widget.source.table]);

  const chartHeight = Math.max(120, height - 86);

  return (
    <Card variant="outlined" sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <CardContent sx={{ pb: 1, flexGrow: 1, display: "flex", flexDirection: "column" }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="subtitle1" fontWeight={600} noWrap>
            {widget.title}
          </Typography>
          {resp && (
            <FreshnessBadge dataAsOf={resp.data_as_of} stale={resp.stale} />
          )}
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}
        {!resp && !error && (
          <Box sx={{ display: "grid", placeItems: "center", flexGrow: 1 }}>
            <CircularProgress size={24} />
          </Box>
        )}
        {resp && !error && (
          <Box sx={{ flexGrow: 1 }}>{renderBody(widget, resp.rows, chartHeight)}</Box>
        )}
      </CardContent>
    </Card>
  );
}

function renderBody(widget: Widget, rows: any[], h: number) {
  const viz = widget.viz || {};

  if (widget.type === "kpi") {
    const value = rows.length ? rows[0][viz.value ?? "value"] : null;
    const num = typeof value === "number" ? value : Number(value);
    const text = isNaN(num) ? "—" : num.toFixed(viz.precision ?? 2);
    return (
      <Box sx={{ display: "grid", placeItems: "center", height: h }}>
        <Box sx={{ textAlign: "center" }}>
          <Typography variant="h3" color="primary">
            {text}
            <Typography component="span" variant="h6" sx={{ ml: 0.5 }}>
              {viz.unit}
            </Typography>
          </Typography>
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
                <TableCell key={c}>{c}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.slice(0, 200).map((r, i) => (
              <TableRow key={i}>
                {cols.map((c) => (
                  <TableCell key={c}>{String(r[c])}</TableCell>
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
          <Pie data={rows} dataKey={viz.y} nameKey={viz.x} outerRadius={Math.min(h / 2 - 10, 110)} label>
            {rows.map((_, i) => (
              <Cell key={i} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  // line / area / bar
  const x = viz.x;
  const y = viz.y;
  const series = viz.series;

  if ((widget.type === "line" || widget.type === "area") && series) {
    const { data, seriesKeys } = pivot(rows, x, series, y);
    const Chart = widget.type === "line" ? LineChart : AreaChart;
    return (
      <ResponsiveContainer width="100%" height={h}>
        <Chart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={x} tickFormatter={fmtX} minTickGap={24} />
          <YAxis />
          <Tooltip labelFormatter={fmtX} />
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
          <Tooltip labelFormatter={fmtX} />
          <Bar dataKey={y} fill={SERIES_COLORS[0]} />
        </BarChart>
      </ResponsiveContainer>
    );
  }

  // line/area without series
  const Chart = widget.type === "area" ? AreaChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height={h}>
      <Chart data={rows}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={x} tickFormatter={fmtX} minTickGap={24} />
        <YAxis />
        <Tooltip labelFormatter={fmtX} />
        {widget.type === "area" ? (
          <Area type="monotone" dataKey={y} stroke={SERIES_COLORS[0]} fill={SERIES_COLORS[0]} fillOpacity={0.25} />
        ) : (
          <Line type="monotone" dataKey={y} stroke={SERIES_COLORS[0]} dot={false} />
        )}
      </Chart>
    </ResponsiveContainer>
  );
}
