export interface CitationEntry {
  source?: string;
  title?: string;
  url?: string;
  score?: number;
  document_id?: string;
  chunk_index?: number;
  chunk_text?: string;
  page?: number | null;
  type: 'document' | 'web';
}

export type CitationMap = Record<string, CitationEntry>;

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  agent_used: string;
  route: string;
  sources: Source[] | HybridSources;
  citation_map: CitationMap;
  processing_time: number | null;
  created_at: string;
  graph?: GraphConfig | null;
  graph_intent?: GraphIntent | null;
  diagnosis?: DiagnosisMetadata | null;
  feedback?: string;
}

export interface Source {
  source?: string;
  title?: string;
  url?: string;
  score?: number;
  document_id?: string;
  chunk_index?: number;
}

export interface HybridSources {
  internal: Source[];
  external: Source[];
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface GraphDataset {
  label: string;
  data: number[];
  borderColor?: string;
  backgroundColor?: string;
  fill?: boolean;
  tension?: number;
  borderWidth?: number;
  pointRadius?: number;
  pointHoverRadius?: number;
}

export interface GraphChartConfig {
  type: string;
  data: {
    labels: string[];
    datasets: GraphDataset[];
  };
  options?: Record<string, unknown>;
}

export interface GraphConfig {
  type: 'chart' | 'summary' | 'table' | 'error';
  chart_type?: 'line' | 'bar' | 'scatter';
  title: string;
  chart_config?: GraphChartConfig;
  raw_data?: Record<string, unknown> | Record<string, unknown>[];
  message?: string;
  summary?: Record<string, unknown>;
  anomalies?: Record<string, unknown>[];
  data?: Record<string, unknown>;
  columns?: string[];
  rows?: (string | number | null)[][];
}

// ─── Vessel & Noon Report Types ──────────────────────────────

export interface Vessel {
  id: string;
  name: string;
  vessel_type: string;
  imo_number: string;
  call_sign?: string;
  flag_state?: string;
  dwt?: number | null;
  grt?: number | null;
  year_built?: number | null;
  fleet_name?: string;
  owner?: string;
  manager?: string;
  operational_status: string;
  main_engine_type?: string;
  noon_report_count: number;
  document_count: number;
}

export interface VesselCreatePayload {
  name: string;
  vessel_type: string;
  imo_number: string;
  call_sign?: string;
  flag_state?: string;
  dwt?: number | null;
  grt?: number | null;
  year_built?: number | null;
  fleet_name?: string;
  owner?: string;
  manager?: string;
  operational_status?: string;
  main_engine_type?: string;
}

export interface NoonReport {
  id: string;
  vessel: string;
  vessel_name: string;
  report_date: string;
  report_time?: string;
  voyage_number?: string;
  latitude?: number | null;
  longitude?: number | null;
  speed_avg?: number | null;
  distance_sailed?: number | null;
  rpm_avg?: number | null;
  fo_consumption?: number | null;
  bf_consumption?: number | null;
  wind_force?: number | null;
  sea_state?: number | null;
  cargo_condition?: string;
  is_validated: boolean;
  created_at: string;
}

export interface NoonReportCreatePayload {
  report_date: string;
  report_time?: string;
  voyage_number?: string;
  latitude?: number | null;
  longitude?: number | null;
  speed_avg?: number | null;
  speed_ordered?: number | null;
  distance_sailed?: number | null;
  rpm_avg?: number | null;
  fo_consumption?: number | null;
  bf_consumption?: number | null;
  wind_force?: number | null;
  sea_state?: number | null;
  cargo_condition?: string;
  remarks?: string;
}

export interface GraphIntent {
  metric: string;
  vessel_name?: string;
  time_range?: string;
  chart_type?: string;
  comparison?: boolean;
}

// ─── Diagnosis Types ─────────────────────────────────────────

export interface DiagnosisTrend {
  metric: string;
  direction: string;
  change_percent: number;
  recent_avg: number;
  baseline_avg: number;
  period: string;
}

export interface DiagnosisAnomaly {
  date: string;
  field: string;
  value: number;
  expected_range: number[];
  label: string;
}

export interface DiagnosisObservation {
  type: string;
  description: string;
  data?: Record<string, number | null>;
}

export interface DiagnosisMetadata {
  symptoms: string[];
  affected_components: string[];
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: string;
  time_context: string;
  data_available: boolean;
  knowledge_available: boolean;
  vessel_name?: string | null;
  observations: DiagnosisObservation[];
  trends: DiagnosisTrend[];
  anomalies: DiagnosisAnomaly[];
}

export interface ChatResponse {
  answer: string;
  agent: string;
  route: string;
  sources: Source[] | HybridSources;
  citation_map: CitationMap;
  session_id: string;
  processing_time: number;
  routing_reasoning: string;
  graph?: GraphConfig | null;
  graph_intent?: GraphIntent | null;
  available_vessels?: string[];
  diagnosis?: DiagnosisMetadata | null;
}

export interface Document {
  id: string;
  title: string;
  file_type: string;
  file_size: number;
  total_pages: number | null;
  total_chunks: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error_message?: string;
  uploaded_at: string;
}

export interface UploadResponse {
  message: string;
  document_id: string;
  title: string;
  status: string;
}

// ─── Dashboard Types ────────────────────────────────────────

export interface DashboardOverview {
  vessels: { total: number; active: number };
  users: { total: number; active_7d: number };
  documents: {
    total: number;
    by_status: Record<string, number>;
    by_embedding: Record<string, number>;
    total_chunks: number;
  };
  queries: {
    total: number;
    last_7d: number;
    route_distribution: Record<string, number>;
    avg_processing_time: number | null;
  };
  noon_reports: { total: number };
  alerts: { unread: number };
  system_health: { errors_24h: number };
  recent_activity: RecentActivity[];
}

export interface RecentActivity {
  id: string;
  query: string;
  route: string;
  agent_used: string;
  processing_time: number | null;
  timestamp: string;
  session_id: string;
}

export interface PaginatedResponse<T> {
  results: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface QueryLogEntry {
  id: string;
  assistant_id: string | null;
  query: string;
  response_preview: string;
  route: string;
  agent_used: string;
  processing_time: number | null;
  feedback: string;
  has_graph: boolean;
  has_diagnosis: boolean;
  timestamp: string;
  session_id: string;
}

export interface QueryDetail {
  user_message: {
    id: string;
    content: string;
    timestamp: string;
  };
  assistant_message: {
    id: string;
    content: string;
    route: string;
    agent_used: string;
    sources: Source[] | HybridSources;
    citation_map: CitationMap;
    graph: GraphConfig | null;
    diagnosis: DiagnosisMetadata | null;
    feedback: string;
    feedback_note: string;
    processing_time: number | null;
    timestamp: string;
  } | null;
  pipeline_logs: PipelineLog[];
}

export interface PipelineLog {
  level: string;
  category: string;
  message: string;
  duration_ms: number | null;
  created_at: string;
}

export interface RagDocStatus {
  id: string;
  title: string;
  file_type: string;
  file_size: number;
  total_pages: number | null;
  total_chunks: number;
  status: string;
  embedding_status: string;
  document_type: string;
  vessel_id: string | null;
  uploaded_at: string;
  processed_at: string | null;
  error_message: string;
}

export interface RagStatusResponse {
  results: RagDocStatus[];
  aggregates: {
    total: number;
    by_status: Record<string, number>;
    by_embedding: Record<string, number>;
    total_chunks: number;
  };
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AnalyticsImportEntry {
  id: string;
  filename: string;
  vessel: string;
  vessel_id: string;
  status: string;
  total_rows: number;
  successful_rows: number;
  failed_rows: number;
  skipped_rows: number;
  created_at: string;
  completed_at: string | null;
}

export interface GraphHistoryEntry {
  id: string;
  query: string;
  chart_type: string;
  title: string;
  processing_time: number | null;
  timestamp: string;
}

export interface AnalyticsMonitorResponse {
  imports: AnalyticsImportEntry[];
  graph_history: GraphHistoryEntry[];
  top_metrics: { metric: string; count: number }[];
  aggregates: {
    total: number;
    by_status: Record<string, number>;
    total_noon_reports: number;
  };
}

export interface DiagnosisEntry {
  id: string;
  query: string;
  severity: string;
  category: string;
  symptoms: string[];
  affected_components: string[];
  vessel_name: string;
  feedback: string;
  processing_time: number | null;
  timestamp: string;
}

export interface DiagnosisMonitorResponse {
  results: DiagnosisEntry[];
  feedback_stats: Record<string, number>;
  severity_distribution: Record<string, number>;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SystemLogEntry {
  id: string;
  level: string;
  category: string;
  message: string;
  details: Record<string, unknown>;
  duration_ms: number | null;
  document_id: string | null;
  session_id: string | null;
  user: string | null;
  created_at: string;
}

export interface SystemLogsResponse {
  results: SystemLogEntry[];
  aggregates: {
    errors_24h: number;
    warnings_24h: number;
    errors_7d: number;
    by_category: Record<string, number>;
    by_level: Record<string, number>;
  };
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AlertEntry {
  id: string;
  alert_type: string;
  severity: string;
  title: string;
  message: string;
  details: Record<string, unknown>;
  vessel_id: string | null;
  vessel_name: string | null;
  is_read: boolean;
  created_at: string;
}

export interface VesselPerformanceData {
  vessel: {
    id: string;
    name: string;
    vessel_type: string;
    imo_number: string;
    operational_status: string;
  };
  period: { from: string; to: string };
  trends: {
    dates: string[];
    fuel: (number | null)[];
    rpm: (number | null)[];
    speed: (number | null)[];
    distance: (number | null)[];
  };
  summary: {
    avg_speed: number | null;
    avg_rpm: number | null;
    avg_fuel: number | null;
    total_distance: number | null;
    total_fuel: number | null;
    report_count: number;
  };
}

export interface SimpleVessel {
  id: string;
  name: string;
  imo_number: string;
  operational_status: string;
}
