import { ReactNode } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Button,
  Chip,
  Container,
  Toolbar,
  Typography,
} from "@mui/material";
import InsightsIcon from "@mui/icons-material/Insights";
import { useAuth } from "../auth/AuthContext";

const NAV = [
  { to: "/dashboards", label: "Dashboards", cap: "project:view" },
  { to: "/catalog", label: "Catalog", cap: "project:view" },
  { to: "/jobs", label: "Jobs", cap: "job:author" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { me, logout, has } = useAuth();
  const loc = useLocation();

  return (
    <Box>
      <AppBar position="sticky" color="default" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar>
          <InsightsIcon sx={{ mr: 1, color: "primary.main" }} />
          <Typography variant="h6" sx={{ mr: 3 }}>
            UPM Platform
          </Typography>
          {NAV.filter((n) => has(n.cap)).map((n) => (
            <Button
              key={n.to}
              component={RouterLink}
              to={n.to}
              color={loc.pathname.startsWith(n.to) ? "primary" : "inherit"}
              sx={{ fontWeight: loc.pathname.startsWith(n.to) ? 700 : 400 }}
            >
              {n.label}
            </Button>
          ))}
          <Box sx={{ flexGrow: 1 }} />
          <Chip
            size="small"
            label={me?.user.email}
            sx={{ mr: 1 }}
            color="primary"
            variant="outlined"
          />
          <Button color="inherit" onClick={logout}>
            Logout
          </Button>
        </Toolbar>
      </AppBar>
      <Container maxWidth="xl" sx={{ py: 3 }}>
        {children}
      </Container>
    </Box>
  );
}
