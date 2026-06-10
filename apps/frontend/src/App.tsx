import { Navigate, Route, Routes } from "react-router-dom";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import { useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CatalogPage from "./pages/CatalogPage";
import DashboardsPage from "./pages/DashboardsPage";
import DashboardViewPage from "./pages/DashboardViewPage";
import DashboardBuilderPage from "./pages/DashboardBuilderPage";
import JobsPage from "./pages/JobsPage";
import JobBuilderPage from "./pages/JobBuilderPage";
import ConnectionsPage from "./pages/ConnectionsPage";
import IngestWizardPage from "./pages/IngestWizardPage";

export default function App() {
  const { me, loading, has } = useAuth();

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

  const canAuthorJobs = has("job:author");
  const canAuthorDash = has("dashboard:author");

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboards" replace />} />
        <Route path="/catalog" element={<CatalogPage />} />
        <Route path="/dashboards" element={<DashboardsPage />} />
        <Route path="/dashboards/:id" element={<DashboardViewPage />} />
        {canAuthorDash && <Route path="/dashboards/new" element={<DashboardBuilderPage />} />}
        {canAuthorDash && <Route path="/dashboards/:id/edit" element={<DashboardBuilderPage />} />}
        {canAuthorJobs && <Route path="/jobs" element={<JobsPage />} />}
        {canAuthorJobs && <Route path="/jobs/new" element={<JobBuilderPage />} />}
        {canAuthorJobs && <Route path="/jobs/:id/edit" element={<JobBuilderPage />} />}
        {canAuthorJobs && <Route path="/ingest" element={<IngestWizardPage />} />}
        {canAuthorJobs && <Route path="/connections" element={<ConnectionsPage />} />}
        <Route path="*" element={<Navigate to="/dashboards" replace />} />
      </Routes>
    </Layout>
  );
}
