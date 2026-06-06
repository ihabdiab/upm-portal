import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Card,
  CardActionArea,
  CardContent,
  CircularProgress,
  Grid,
  Typography,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/SpaceDashboard";
import { api } from "../api/client";
import type { DashboardSummary, ProjectOut } from "../api/types";

export default function DashboardsPage() {
  const nav = useNavigate();
  const [projects, setProjects] = useState<ProjectOut[] | null>(null);
  const [byProject, setByProject] = useState<Record<number, DashboardSummary[]>>({});

  useEffect(() => {
    api.get<ProjectOut[]>("/projects").then(async ({ data }) => {
      setProjects(data);
      const map: Record<number, DashboardSummary[]> = {};
      await Promise.all(
        data.map(async (p) => {
          const { data: ds } = await api.get<DashboardSummary[]>(`/projects/${p.id}/dashboards`);
          map[p.id] = ds;
        }),
      );
      setByProject(map);
    });
  }, []);

  if (!projects) return <CircularProgress />;

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Dashboards
      </Typography>
      {projects.length === 0 && (
        <Typography color="text.secondary">You don't have access to any projects yet.</Typography>
      )}
      {projects.map((p) => (
        <Box key={p.id} sx={{ mb: 4 }}>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            {p.name} · {p.role}
          </Typography>
          <Grid container spacing={2}>
            {(byProject[p.id] ?? []).map((d) => (
              <Grid item xs={12} sm={6} md={4} key={d.id}>
                <Card variant="outlined">
                  <CardActionArea onClick={() => nav(`/dashboards/${d.id}`)}>
                    <CardContent>
                      <DashboardIcon color="primary" />
                      <Typography variant="h6">{d.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        v{d.version}
                      </Typography>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            ))}
            {(byProject[p.id] ?? []).length === 0 && (
              <Grid item xs={12}>
                <Typography color="text.secondary" variant="body2">
                  No dashboards in this project.
                </Typography>
              </Grid>
            )}
          </Grid>
        </Box>
      ))}
    </Box>
  );
}
