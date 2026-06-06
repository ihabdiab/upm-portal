import { createTheme } from "@mui/material/styles";

// MUI v6 with Material-3 color roles (ADR-009). Pragmatic M3 theming, not pixel-exact.
export const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: "light",
    primary: { main: "#3f5aa9" },
    secondary: { main: "#5a6b9c" },
    background: { default: "#f6f7fb", paper: "#ffffff" },
    success: { main: "#2e7d32" },
    warning: { main: "#ed6c02" },
    error: { main: "#c62828" },
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: "Roboto, system-ui, -apple-system, Segoe UI, sans-serif",
    h6: { fontWeight: 600 },
  },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
    MuiButton: { defaultProps: { disableElevation: true } },
  },
});

// Stable palette for chart series.
export const SERIES_COLORS = [
  "#3f5aa9",
  "#ed6c02",
  "#2e7d32",
  "#9c27b0",
  "#0288d1",
  "#c62828",
  "#5d4037",
  "#00897b",
];
