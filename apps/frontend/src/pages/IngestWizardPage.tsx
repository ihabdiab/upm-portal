import { useState } from "react";
import { Box, Tab, Tabs, Typography } from "@mui/material";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import StorageIcon from "@mui/icons-material/Storage";
import TerminalIcon from "@mui/icons-material/Terminal";
import CsvIngest from "../components/ingest/CsvIngest";
import ConnectionIngest from "../components/ingest/ConnectionIngest";
import SqlIngest from "../components/ingest/SqlIngest";

/** Unified ingestion menu (§1.1) — the three pathways into DuckDB:
 *  A) a saved RDBMS connection · B) CSV upload · C) a DuckDB SELECT (transform). */
export default function IngestWizardPage() {
  const [tab, setTab] = useState(0);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Ingest data
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Three ways in. Whatever the source, the result is a scheduled job that materializes a
        DuckDB table — it then appears in the Catalog and is usable in dashboards.
      </Typography>

      <Tabs
        value={tab}
        onChange={(_, v) => setTab(v)}
        sx={{ mb: 3, borderBottom: 1, borderColor: "divider" }}
        variant="scrollable"
        allowScrollButtonsMobile
      >
        <Tab icon={<UploadFileIcon />} iconPosition="start" label="CSV file" />
        <Tab icon={<StorageIcon />} iconPosition="start" label="From connection" />
        <Tab icon={<TerminalIcon />} iconPosition="start" label="DuckDB SQL" />
      </Tabs>

      {tab === 0 && <CsvIngest />}
      {tab === 1 && <ConnectionIngest />}
      {tab === 2 && <SqlIngest />}
    </Box>
  );
}
