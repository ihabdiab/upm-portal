import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Tooltip from "@mui/material/Tooltip";

function fmt(ts?: string | null): string {
  if (!ts) return "never";
  const d = new Date(ts);
  return d.toLocaleString();
}

/** "Data as of ..." with an amber stale badge / red failed badge (§10).
 * `compact` renders a small status dot with the detail in a tooltip — used inside
 * widget headers where a full chip would crowd the title. */
export default function FreshnessBadge({
  dataAsOf,
  stale,
  status,
  compact = false,
}: {
  dataAsOf?: string | null;
  stale?: boolean;
  status?: string | null;
  compact?: boolean;
}) {
  const failed = status === "failed";
  const color = failed ? "error.main" : stale ? "warning.main" : "success.main";
  const text = failed
    ? "Last load FAILED"
    : `Data as of ${fmt(dataAsOf)}${stale ? " · STALE (older than expected for this feed)" : ""}`;

  if (compact) {
    return (
      <Tooltip title={text}>
        <Box
          component="span"
          sx={{
            width: 9,
            height: 9,
            borderRadius: "50%",
            bgcolor: color,
            flexShrink: 0,
            display: "inline-block",
          }}
        />
      </Tooltip>
    );
  }

  if (failed) return <Chip size="small" color="error" label="last load failed" />;
  if (stale) {
    return (
      <Tooltip title="Data is older than expected for this feed's schedule">
        <Chip size="small" color="warning" label={`Data as of ${fmt(dataAsOf)} · stale`} />
      </Tooltip>
    );
  }
  return <Chip size="small" color="success" variant="outlined" label={`Data as of ${fmt(dataAsOf)}`} />;
}
