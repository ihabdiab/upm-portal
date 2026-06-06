import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

function fmt(ts?: string | null): string {
  if (!ts) return "never";
  const d = new Date(ts);
  return d.toLocaleString();
}

/** "Data as of ..." with an amber stale badge / red failed badge (§10). */
export default function FreshnessBadge({
  dataAsOf,
  stale,
  status,
}: {
  dataAsOf?: string | null;
  stale?: boolean;
  status?: string | null;
}) {
  if (status === "failed") {
    return <Chip size="small" color="error" label="last load failed" />;
  }
  const label = `Data as of ${fmt(dataAsOf)}`;
  if (stale) {
    return (
      <Tooltip title="Data is older than expected for this feed's schedule">
        <Chip size="small" color="warning" label={`${label} · stale`} />
      </Tooltip>
    );
  }
  return <Chip size="small" color="success" variant="outlined" label={label} />;
}
