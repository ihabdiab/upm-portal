import { createTheme } from "@mui/material/styles";

// MUI v6 with Material-3 color roles (ADR-009). Mobile-first: the same theme will serve
// the future Android/mobile clients of this portal, so spacing/typography scale cleanly.
export const theme = createTheme({
  cssVariables: true,
  palette: {
    mode: "light",
    primary: { main: "#4355b9" },
    secondary: { main: "#00696e" },
    background: { default: "#f4f6fb", paper: "#ffffff" },
    success: { main: "#2e7d32" },
    warning: { main: "#b26a00" },
    error: { main: "#ba1a1a" },
    divider: "rgba(60, 64, 90, 0.14)",
  },
  shape: { borderRadius: 14 },
  typography: {
    fontFamily:
      "Inter, Roboto, system-ui, -apple-system, 'Segoe UI', sans-serif",
    h5: { fontWeight: 700, letterSpacing: -0.3 },
    h6: { fontWeight: 650 },
    subtitle1: { fontWeight: 600 },
    subtitle2: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  components: {
    MuiPaper: { styleOverrides: { root: { backgroundImage: "none" } } },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: { root: { borderRadius: 10 } },
    },
    MuiCard: {
      styleOverrides: {
        root: ({ theme: t }) => ({
          borderColor: t.palette.divider,
          transition: "box-shadow .15s ease",
        }),
      },
    },
    MuiChip: { styleOverrides: { root: { fontWeight: 500 } } },
    MuiTextField: { defaultProps: { size: "small" } },
    MuiTableCell: { styleOverrides: { head: { fontWeight: 650 } } },
    MuiTooltip: { defaultProps: { arrow: true } },
  },
});

// Stable palette for chart series.
export const SERIES_COLORS = [
  "#4355b9",
  "#e8710a",
  "#188038",
  "#9334e6",
  "#0288d1",
  "#d93025",
  "#f29900",
  "#00696e",
];
