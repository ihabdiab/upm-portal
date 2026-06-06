import { useEffect, useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { api } from "../api/client";
import type { TableSummary } from "../api/types";
import FreshnessBadge from "../components/FreshnessBadge";

export default function CatalogPage() {
  const [tables, setTables] = useState<TableSummary[] | null>(null);

  useEffect(() => {
    api.get<TableSummary[]>("/catalog/tables").then(({ data }) => setTables(data));
  }, []);

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Data Catalog
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Registry-backed — these are the materialized DuckDB tables dashboards read. Oracle is
        never touched here.
      </Typography>
      {!tables ? (
        <CircularProgress />
      ) : (
        <Card variant="outlined">
          <CardContent>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Table</TableCell>
                    <TableCell align="right">Rows</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Freshness</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tables.map((t) => (
                    <TableRow key={t.table_name} hover>
                      <TableCell>
                        <Typography fontWeight={600}>{t.table_name}</Typography>
                      </TableCell>
                      <TableCell align="right">{t.row_count.toLocaleString()}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={t.last_load_status ?? "—"}
                          color={
                            t.last_load_status === "success"
                              ? "success"
                              : t.last_load_status === "failed"
                                ? "error"
                                : "default"
                          }
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <FreshnessBadge
                          dataAsOf={t.last_load_succeeded_at}
                          stale={t.stale}
                          status={t.last_load_status}
                        />
                      </TableCell>
                    </TableRow>
                  ))}
                  {tables.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4}>
                        <Stack alignItems="center" sx={{ py: 3 }}>
                          <Typography color="text.secondary">
                            No visible tables yet. Run a job to materialize one.
                          </Typography>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
