import { Navigate, Route, Routes } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CatalogPage from "./pages/CatalogPage";
import DashboardsPage from "./pages/DashboardsPage";
import DashboardViewPage from "./pages/DashboardViewPage";
import JobsPage from "./pages/JobsPage";

export default function App() {
  const { me, loading } = useAuth();

  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!me) {
    return (
      <Routes>
        <Route path="*" element={<LoginPage />} />
      </Routes>
    );
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboards" replace />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/dashboards" element={<DashboardsPage />} />
        <Route path="/dashboards/:id" element={<DashboardViewPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="*" element={<Navigate to="/dashboards" replace />} />
      </Routes>
    </Layout>
  );
}
