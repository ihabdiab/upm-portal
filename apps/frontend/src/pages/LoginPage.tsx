import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import InsightsIcon from "@mui/icons-material/Insights";
import { useAuth } from "../auth/AuthContext";

const DEMO = [
  ["admin@upm.com", "admin12345"],
  ["builder@upm.com", "builder12345"],
  ["viewer@upm.com", "viewer12345"],
];

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("viewer@upm.com");
  const [password, setPassword] = useState("viewer12345");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Box sx={{ display: "grid", placeItems: "center", minHeight: "100vh", p: 2 }}>
      <Card sx={{ width: 400 }} elevation={3}>
        <CardContent>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
            <InsightsIcon color="primary" />
            <Typography variant="h5" fontWeight={700}>
              UPM Platform
            </Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Telecom IT-OSS Unified Performance Management
          </Typography>
          <form onSubmit={submit}>
            <Stack spacing={2}>
              <TextField label="Email" value={email} onChange={(e) => setEmail(e.target.value)} fullWidth />
              <TextField
                label="Password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                fullWidth
              />
              {error && <Alert severity="error">{error}</Alert>}
              <Button type="submit" variant="contained" disabled={busy} size="large">
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            </Stack>
          </form>
          <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>
            Demo accounts:
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 0.5, flexWrap: "wrap" }}>
            {DEMO.map(([e, p]) => (
              <Button
                key={e}
                size="small"
                variant="outlined"
                onClick={() => {
                  setEmail(e);
                  setPassword(p);
                }}
              >
                {e.split("@")[0]}
              </Button>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
