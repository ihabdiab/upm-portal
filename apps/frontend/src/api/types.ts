// Mirrors the backend contracts (upm_shared). Kept hand-written for v1; can be generated.

export interface UserOut {
  id: number;
  email: string;
  full_name?: string | null;
  is_active: boolean;
}

export interface ProjectMembership {
  project_id: number;
  project_name: string;
  role: string;
}

export interface MeResponse {
  user: UserOut;
  capabilities: string[];
  projects: ProjectMembership[];
}

export interface TokenResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  user?: UserOut;
}

export interface TableSummary {
  table_name: string;
  row_count: number;
  last_load_succeeded_at?: string | null;
  last_load_status?: string | null;
  is_visible: boolean;
  stale: boolean;
}

export interface ColumnInfo {
  name: string;
  type: string;
  comment?: string | null;
}

export interface Freshness {
  last_load_started_at?: string | null;
  last_load_succeeded_at?: string | null;
  last_load_status?: string | null;
  last_watermark_value?: string | null;
  table_version: number;
  row_count: number;
  stale: boolean;
}

export interface TableDetail {
  table_name: string;
  columns: ColumnInfo[];
  freshness: Freshness;
  sample_rows?: Record<string, unknown>[] | null;
}

export interface QueryResponse {
  rows: Record<string, any>[];
  page: number;
  total?: number | null;
  table_version: number;
  data_as_of?: string | null;
  stale: boolean;
  cached: boolean;
}

export interface Widget {
  id: string;
  type: "line" | "bar" | "area" | "pie" | "scatter" | "kpi" | "table" | "map";
  title: string;
  source: { table: string; table_version_pin?: number | null };
  query: Record<string, any>;
  viz: Record<string, any>;
  grid: { x: number; y: number; w: number; h: number };
}

export interface DashboardDefinition {
  version: number;
  layout: { cols: number; rowHeight: number };
  widgets: Widget[];
}

export interface DashboardSummary {
  id: number;
  project_id: number;
  name: string;
  version: number;
  updated_at?: string | null;
}

export interface DashboardOut extends DashboardSummary {
  definition: DashboardDefinition;
}

export interface ProjectOut {
  id: number;
  name: string;
  description?: string | null;
  role: string;
}

export interface JobOut {
  id: number;
  is_enabled: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  definition: Record<string, any>;
}

export interface RunOut {
  id: number;
  attempt: number;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  rows_read: number;
  rows_written: number;
  watermark_after?: string | null;
  error?: string | null;
}
