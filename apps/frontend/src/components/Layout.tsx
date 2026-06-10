import { ReactNode, useState } from "react";
import { Link as RouterLink, useLocation } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Button,
  Container,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import InsightsIcon from "@mui/icons-material/Insights";
import SpaceDashboardOutlinedIcon from "@mui/icons-material/SpaceDashboardOutlined";
import TableViewOutlinedIcon from "@mui/icons-material/TableViewOutlined";
import UploadFileOutlinedIcon from "@mui/icons-material/UploadFileOutlined";
import WorkHistoryOutlinedIcon from "@mui/icons-material/WorkHistoryOutlined";
import CableOutlinedIcon from "@mui/icons-material/CableOutlined";
import LogoutIcon from "@mui/icons-material/Logout";
import { useAuth } from "../auth/AuthContext";

const NAV = [
  { to: "/dashboards", label: "Dashboards", cap: "project:view", icon: <SpaceDashboardOutlinedIcon /> },
  { to: "/catalog", label: "Catalog", cap: "project:view", icon: <TableViewOutlinedIcon /> },
  { to: "/ingest", label: "Ingest", cap: "job:author", icon: <UploadFileOutlinedIcon /> },
  { to: "/jobs", label: "Jobs", cap: "job:author", icon: <WorkHistoryOutlinedIcon /> },
  { to: "/connections", label: "Connections", cap: "job:author", icon: <CableOutlinedIcon /> },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { me, logout, has } = useAuth();
  const loc = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [userMenu, setUserMenu] = useState<null | HTMLElement>(null);

  const nav = NAV.filter((n) => has(n.cap));
  const initials = (me?.user.full_name || me?.user.email || "?")
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  return (
    <Box sx={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <AppBar
        position="sticky"
        color="inherit"
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          bgcolor: "rgba(255,255,255,0.85)",
          backdropFilter: "blur(8px)",
        }}
      >
        <Toolbar sx={{ gap: 0.5 }}>
          {/* Mobile: hamburger -> drawer */}
          <IconButton
            edge="start"
            sx={{ display: { xs: "inline-flex", md: "none" }, mr: 0.5 }}
            onClick={() => setDrawerOpen(true)}
            aria-label="open navigation"
          >
            <MenuIcon />
          </IconButton>

          <InsightsIcon sx={{ mr: 1, color: "primary.main" }} />
          <Typography variant="h6" sx={{ mr: 3, whiteSpace: "nowrap" }}>
            UPM Platform
          </Typography>

          {/* Desktop nav */}
          <Box sx={{ display: { xs: "none", md: "flex" }, gap: 0.5 }}>
            {nav.map((n) => {
              const active = loc.pathname.startsWith(n.to);
              return (
                <Button
                  key={n.to}
                  component={RouterLink}
                  to={n.to}
                  size="small"
                  color={active ? "primary" : "inherit"}
                  sx={{
                    px: 1.5,
                    fontWeight: active ? 700 : 500,
                    bgcolor: active ? "action.selected" : "transparent",
                  }}
                >
                  {n.label}
                </Button>
              );
            })}
          </Box>

          <Box sx={{ flexGrow: 1 }} />

          <Tooltip title={me?.user.email ?? ""}>
            <IconButton onClick={(e) => setUserMenu(e.currentTarget)} size="small">
              <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main", fontSize: 14 }}>
                {initials}
              </Avatar>
            </IconButton>
          </Tooltip>
          <Menu anchorEl={userMenu} open={!!userMenu} onClose={() => setUserMenu(null)}>
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="subtitle2">{me?.user.full_name || me?.user.email}</Typography>
              <Typography variant="caption" color="text.secondary">
                {me?.user.email}
              </Typography>
            </Box>
            <Divider />
            <MenuItem onClick={() => { setUserMenu(null); logout(); }}>
              <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
              Logout
            </MenuItem>
          </Menu>
        </Toolbar>
      </AppBar>

      {/* Mobile drawer */}
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <Box sx={{ width: 260 }} role="presentation">
          <Box sx={{ display: "flex", alignItems: "center", gap: 1, p: 2 }}>
            <InsightsIcon color="primary" />
            <Typography variant="h6">UPM Platform</Typography>
          </Box>
          <Divider />
          <List>
            {nav.map((n) => (
              <ListItemButton
                key={n.to}
                component={RouterLink}
                to={n.to}
                selected={loc.pathname.startsWith(n.to)}
                onClick={() => setDrawerOpen(false)}
              >
                <ListItemIcon>{n.icon}</ListItemIcon>
                <ListItemText primary={n.label} />
              </ListItemButton>
            ))}
          </List>
        </Box>
      </Drawer>

      <Container maxWidth="xl" sx={{ py: { xs: 2, md: 3 }, flexGrow: 1 }}>
        {children}
      </Container>
    </Box>
  );
}
