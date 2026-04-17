import axios from 'axios';
import type {
  ChatResponse, ChatSession, ChatMessage, Document, UploadResponse,
  Vessel, VesselCreatePayload, NoonReport, NoonReportCreatePayload,
  DashboardOverview, PaginatedResponse, QueryLogEntry, QueryDetail,
  RagStatusResponse, AnalyticsMonitorResponse, DiagnosisMonitorResponse,
  SystemLogsResponse, AlertEntry, VesselPerformanceData, SimpleVessel,
} from '@/types';

// Helper to read a cookie by name
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Attach CSRF token to every mutating request
api.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken && config.headers) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// ─── Chat ────────────────────────────────────────────────────
export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const payload: { message: string; session_id?: string } = { message };
  if (sessionId) payload.session_id = sessionId;
  const { data } = await api.post<ChatResponse>('/chat/', payload);
  return data;
}

export async function fetchSessions(): Promise<ChatSession[]> {
  const { data } = await api.get<{ sessions: ChatSession[] }>('/sessions/');
  return data.sessions ?? [];
}

export async function fetchSessionMessages(
  sessionId: string
): Promise<ChatMessage[]> {
  const { data } = await api.get<{ session_id: string; messages: ChatMessage[] }>(
    `/sessions/${sessionId}/messages/`
  );
  return data.messages;
}

// ─── Feedback ────────────────────────────────────────────────
export async function submitMessageFeedback(
  messageId: string,
  feedback: 'correct' | 'incorrect' | 'partial',
  note?: string
): Promise<{ status: string; message_id: string; feedback: string }> {
  const { data } = await api.post<{ status: string; message_id: string; feedback: string }>(
    `/messages/${messageId}/feedback/`,
    { feedback, note: note ?? '' }
  );
  return data;
}

// ─── Documents ───────────────────────────────────────────────
const ingestionApi = axios.create({
  baseURL: '/ingestion/api',
  withCredentials: true,
});

// Attach CSRF token to ingestion API requests
ingestionApi.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken && config.headers) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

export async function uploadDocument(file: File, title?: string): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title ?? file.name);
  const { data } = await ingestionApi.post<UploadResponse>('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function fetchDocuments(): Promise<Document[]> {
  const { data } = await ingestionApi.get<{ documents: Document[] }>('/documents/');
  return data.documents;
}

export async function fetchDocumentStatus(documentId: string): Promise<Document> {
  const { data } = await ingestionApi.get<Document>(`/documents/${documentId}/status/`);
  return data;
}

export async function deleteDocument(documentId: string): Promise<{ message: string; vectors_deleted: number }> {
  const { data } = await ingestionApi.delete<{ message: string; vectors_deleted: number }>(
    `/documents/${documentId}/delete/`
  );
  return data;
}

// ─── Auth ────────────────────────────────────────────────────
export interface AuthUser {
  username: string;
  email: string;
  role?: string;
}

export async function apiLogin(email: string, password: string): Promise<AuthUser> {
  const { data } = await api.post<{ success: boolean; user: AuthUser }>('/auth/login/', {
    email,
    password,
  });
  return data.user;
}

export async function apiLogout(): Promise<void> {
  await api.post('/auth/logout/');
}

export async function apiCheckSession(): Promise<AuthUser | null> {
  try {
    const { data } = await api.get<{ authenticated: boolean; user: AuthUser }>('/auth/session/');
    return data.authenticated ? data.user : null;
  } catch {
    return null;
  }
}

export async function fetchCsrfToken(): Promise<void> {
  await api.get('/auth/csrf/');
}

// ─── Analytics API ───────────────────────────────────────────
const analyticsApi = axios.create({
  baseURL: '/api/analytics',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

analyticsApi.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken && config.headers) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

// Vessels
export async function fetchVessels(): Promise<Vessel[]> {
  const { data } = await analyticsApi.get<Vessel[]>('/vessels/');
  return data;
}

export async function createVessel(payload: VesselCreatePayload): Promise<Vessel> {
  const { data } = await analyticsApi.post<Vessel>('/vessels/create/', payload);
  return data;
}

// Noon Reports
export async function fetchNoonReports(vesselId: string, page = 1): Promise<{ total: number; results: NoonReport[] }> {
  const { data } = await analyticsApi.get<{ total: number; page: number; page_size: number; results: NoonReport[] }>(
    `/vessels/${vesselId}/noon-reports/?page=${page}&page_size=50`
  );
  return data;
}

export async function createNoonReport(vesselId: string, payload: NoonReportCreatePayload): Promise<NoonReport> {
  const { data } = await analyticsApi.post<NoonReport>(`/vessels/${vesselId}/noon-reports/create/`, payload);
  return data;
}

// Delete Vessel
export async function deleteVessel(vesselId: string): Promise<void> {
  await analyticsApi.delete(`/vessels/${vesselId}/delete/`);
}

// Delete Noon Report
export async function deleteNoonReport(vesselId: string, reportId: string): Promise<void> {
  await analyticsApi.delete(`/vessels/${vesselId}/noon-reports/${reportId}/delete/`);
}

// ── CSV Export / Import ──────────────────────────────────────

export async function exportVesselsCsv(): Promise<void> {
  const response = await analyticsApi.get('/vessels/export/csv/', { responseType: 'blob' });
  _downloadBlob(response.data as Blob, 'vessels.csv');
}

export async function downloadVesselTemplate(): Promise<void> {
  const response = await analyticsApi.get('/vessels/template/csv/', { responseType: 'blob' });
  _downloadBlob(response.data as Blob, 'vessels_template.csv');
}

export async function importVesselsCsv(file: File): Promise<{ created: number; skipped: number; errors: string[] }> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await analyticsApi.post<{ created: number; skipped: number; errors: string[] }>(
    '/vessels/import/csv/', formData, { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
}

export async function exportNoonReportsCsv(vesselId: string, vesselName: string): Promise<void> {
  const response = await analyticsApi.get(`/vessels/${vesselId}/noon-reports/export/csv/`, { responseType: 'blob' });
  const safeName = vesselName.replace(/\s+/g, '_');
  _downloadBlob(response.data as Blob, `noon_reports_${safeName}.csv`);
}

export async function downloadNoonReportTemplate(): Promise<void> {
  const response = await analyticsApi.get('/templates/noon-reports/csv/', { responseType: 'blob' });
  _downloadBlob(response.data as Blob, 'noon_reports_template.csv');
}

export async function importNoonReportsCsv(vesselId: string, file: File): Promise<{ created: number; skipped: number; errors: string[] }> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await analyticsApi.post<{ created: number; skipped: number; errors: string[] }>(
    `/vessels/${vesselId}/noon-reports/import/csv/`, formData, { headers: { 'Content-Type': 'multipart/form-data' } }
  );
  return data;
}

function _downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

// ─── Dashboard API ───────────────────────────────────────────
const dashboardApi = axios.create({
  baseURL: '/api/dashboard',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

dashboardApi.interceptors.request.use((config) => {
  const csrfToken = getCookie('csrftoken');
  if (csrfToken && config.headers) {
    config.headers['X-CSRFToken'] = csrfToken;
  }
  return config;
});

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const { data } = await dashboardApi.get<DashboardOverview>('/overview/');
  return data;
}

export async function fetchQueryLogs(params?: Record<string, string>): Promise<PaginatedResponse<QueryLogEntry>> {
  const { data } = await dashboardApi.get<PaginatedResponse<QueryLogEntry>>('/queries/', { params });
  return data;
}

export async function fetchQueryDetail(messageId: string): Promise<QueryDetail> {
  const { data } = await dashboardApi.get<QueryDetail>(`/queries/${messageId}/`);
  return data;
}

export async function fetchRagStatus(params?: Record<string, string>): Promise<RagStatusResponse> {
  const { data } = await dashboardApi.get<RagStatusResponse>('/rag/', { params });
  return data;
}

export async function reindexDocument(documentId: string): Promise<{ message: string }> {
  const { data } = await dashboardApi.post<{ message: string }>(`/rag/${documentId}/reindex/`);
  return data;
}

export async function fetchAnalyticsMonitor(params?: Record<string, string>): Promise<AnalyticsMonitorResponse> {
  const { data } = await dashboardApi.get<AnalyticsMonitorResponse>('/analytics-monitor/', { params });
  return data;
}

export async function fetchDiagnosisMonitor(params?: Record<string, string>): Promise<DiagnosisMonitorResponse> {
  const { data } = await dashboardApi.get<DiagnosisMonitorResponse>('/diagnosis/', { params });
  return data;
}

export async function fetchSystemLogs(params?: Record<string, string>): Promise<SystemLogsResponse> {
  const { data } = await dashboardApi.get<SystemLogsResponse>('/logs/', { params });
  return data;
}

export async function fetchAlerts(params?: Record<string, string>): Promise<PaginatedResponse<AlertEntry>> {
  const { data } = await dashboardApi.get<PaginatedResponse<AlertEntry>>('/alerts/', { params });
  return data;
}

export async function markAlertRead(alertId: string): Promise<void> {
  await dashboardApi.post(`/alerts/${alertId}/read/`);
}

export async function markAllAlertsRead(): Promise<void> {
  await dashboardApi.post('/alerts/read-all/');
}

export async function fetchVesselPerformance(
  vesselId: string, params?: Record<string, string>
): Promise<VesselPerformanceData> {
  const { data } = await dashboardApi.get<VesselPerformanceData>(`/vessels/${vesselId}/performance/`, { params });
  return data;
}

export async function fetchDashboardVessels(): Promise<SimpleVessel[]> {
  const { data } = await dashboardApi.get<SimpleVessel[]>('/vessels/');
  return data;
}
