import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { api } from "../api/client";
import type { DashboardOut } from "../api/types";
import WidgetRenderer from "../components/WidgetRenderer";

export default function DashboardViewPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const [dash, setDash] = useState<DashboardOut | null>(null);

  useEffect(() => {
    api.get<DashboardOut>(`/dashboards/${id}`).then(({ data }) => setDash(data));
  }, [id]);

  if (!dash) return <CircularProgress />;

  const cols = dash.definition.layout?.cols ?? 12;
  const rowHeight = dash.definition.layout?.rowHeight ?? 40;

  return (
    <Box>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 2 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => nav("/dashboards")}>
          Back
        </Button>
        <Typography variant="h5">{dash.name}</Typography>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridAutoRows: `${rowHeight}px`,
          gap: 2,
        }}
      >
        {dash.definition.widgets.map((w) => (
          <Box
            key={w.id}
            sx={{
              gridColumn: { xs: "1 / -1", md: `${w.grid.x + 1} / span ${w.grid.w}` },
              gridRow: { md: `${w.grid.y + 1} / span ${w.grid.h}` },
              minHeight: w.grid.h * rowHeight,
            }}
          >
            <WidgetRenderer widget={w} height={w.grid.h * rowHeight} />
          </Box>
        ))}
      </Box>
    </Box>
  );
}
