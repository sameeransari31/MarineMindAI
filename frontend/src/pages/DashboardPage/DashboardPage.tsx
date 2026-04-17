import { useState, useEffect, useCallback, type FC } from 'react';
import {
  HiOutlineChartBarSquare,
  HiOutlineMagnifyingGlass,
  HiOutlineDocumentText,
  HiOutlineChartPie,
  HiOutlineWrenchScrewdriver,
  HiOutlineServerStack,
  HiOutlineBellAlert,
  HiOutlineTruck,
  HiOutlineArrowPath,
  HiOutlineXMark,
} from 'react-icons/hi2';
import {
  fetchDashboardOverview,
  fetchQueryLogs,
  fetchQueryDetail,
  fetchRagStatus,
  reindexDocument,
  fetchAnalyticsMonitor,
  fetchDiagnosisMonitor,
  fetchSystemLogs,
  fetchAlerts,
  markAlertRead,
  markAllAlertsRead,
  fetchVesselPerformance,
  fetchDashboardVessels,
} from '@/api';
import type {
  DashboardOverview,
  QueryLogEntry,
  QueryDetail,
  RagStatusResponse,
  AnalyticsMonitorResponse,
  DiagnosisMonitorResponse,
  SystemLogsResponse,
  AlertEntry,
  VesselPerformanceData,
  SimpleVessel,
} from '@/types';
import { Line, Doughnut, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js';
import styles from './DashboardPage.module.css';

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement,
  BarElement, ArcElement, Filler, Tooltip, Legend
);

type TabId = 'overview' | 'queries' | 'rag' | 'analytics' | 'diagnosis' | 'logs' | 'alerts' | 'vessels';

const TABS: { id: TabId; label: string; icon: typeof HiOutlineChartBarSquare }[] = [
  { id: 'overview', label: 'Overview', icon: HiOutlineChartBarSquare },
  { id: 'vessels', label: 'Vessels', icon: HiOutlineTruck },
  { id: 'queries', label: 'Queries', icon: HiOutlineMagnifyingGlass },
  { id: 'rag', label: 'RAG', icon: HiOutlineDocumentText },
  { id: 'analytics', label: 'Analytics', icon: HiOutlineChartPie },
  { id: 'diagnosis', label: 'Diagnosis', icon: HiOutlineWrenchScrewdriver },
  { id: 'logs', label: 'Logs', icon: HiOutlineServerStack },
  { id: 'alerts', label: 'Alerts', icon: HiOutlineBellAlert },
];

const ROUTE_COLORS: Record<string, string> = {
  rag: '#00b4d8',
  graph: '#34d399',
  diagnosis: '#fbbf24',
  internet: '#a78bfa',
  hybrid: '#f472b6',
};

const SEVERITY_BADGE: Record<string, string> = {
  info: 'badgeBlue',
  warning: 'badgeYellow',
  error: 'badgeRed',
  critical: 'badgeRed',
  low: 'badgeGreen',
  medium: 'badgeYellow',
  high: 'badgeRed',
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
  });
}

// ═════════════════════════════════════════════════════════════════════════════
// MAIN DASHBOARD PAGE
// ═════════════════════════════════════════════════════════════════════════════

const DashboardPage: FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [unreadAlerts, setUnreadAlerts] = useState(0);

  const loadOverview = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchDashboardOverview();
      setOverview(data);
      setUnreadAlerts(data.alerts.unread);
      setLastUpdated(new Date());
    } catch (e) {
      console.error('Failed to load overview', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  return (
    <div className={styles.page}>
      {/* Top bar */}
      <div className={styles.topbar}>
        <div className={styles.topbarLeft}>
          <span className={styles.title}>Dashboard</span>
          {lastUpdated && (
            <span className={styles.lastUpdated}>
              Updated {lastUpdated.toLocaleTimeString()}
            </span>
          )}
        </div>
        <button className={styles.refreshBtn} onClick={loadOverview} disabled={loading}>
          <HiOutlineArrowPath size={14} className={loading ? 'spinning' : ''} />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div className={styles.tabs}>
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            className={`${styles.tab} ${activeTab === id ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(id)}
          >
            <Icon size={16} />
            {label}
            {id === 'alerts' && unreadAlerts > 0 && (
              <span className={styles.tabBadge}>{unreadAlerts}</span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className={styles.content}>
        {activeTab === 'overview' && <OverviewTab overview={overview} loading={loading} />}
        {activeTab === 'vessels' && <VesselPerformanceTab />}
        {activeTab === 'queries' && <QueryMonitorTab />}
        {activeTab === 'rag' && <RagMonitorTab />}
        {activeTab === 'analytics' && <AnalyticsMonitorTab />}
        {activeTab === 'diagnosis' && <DiagnosisMonitorTab />}
        {activeTab === 'logs' && <SystemLogsTab />}
        {activeTab === 'alerts' && <AlertsTab onUpdate={() => loadOverview()} />}
      </div>
    </div>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// OVERVIEW TAB
// ═════════════════════════════════════════════════════════════════════════════

const OverviewTab: FC<{ overview: DashboardOverview | null; loading: boolean }> = ({ overview, loading }) => {
  if (loading && !overview) {
    return <div className={styles.loading}><div className={styles.spinner} /> Loading dashboard...</div>;
  }
  if (!overview) return null;

  const routeDist = overview.queries.route_distribution;
  const routeTotal = Object.values(routeDist).reduce((a, b) => a + b, 0) || 1;

  const doughnutData = {
    labels: Object.keys(routeDist).map(r => r.charAt(0).toUpperCase() + r.slice(1)),
    datasets: [{
      data: Object.values(routeDist),
      backgroundColor: Object.keys(routeDist).map(r => ROUTE_COLORS[r] || '#5e7f9e'),
      borderWidth: 0,
    }],
  };

  return (
    <>
      {/* KPI Cards */}
      <div className={styles.statsGrid}>
        <StatCard label="Total Vessels" value={overview.vessels.total}
          sub={`${overview.vessels.active} active`} color="blue" icon={<HiOutlineTruck size={16} />} />
        <StatCard label="Active Users" value={overview.users.total}
          sub={`${overview.users.active_7d} active this week`} color="green" icon={<HiOutlineChartBarSquare size={16} />} />
        <StatCard label="Documents Indexed" value={overview.documents.total}
          sub={`${overview.documents.total_chunks} chunks`} color="blue" icon={<HiOutlineDocumentText size={16} />} />
        <StatCard label="Total Queries" value={overview.queries.total}
          sub={`${overview.queries.last_7d} this week`} color="green" icon={<HiOutlineMagnifyingGlass size={16} />} />
        <StatCard label="Noon Reports" value={overview.noon_reports.total}
          sub="Total imported" color="yellow" icon={<HiOutlineChartPie size={16} />} />
        <StatCard label="Avg Response Time" value={overview.queries.avg_processing_time ? `${overview.queries.avg_processing_time}s` : 'N/A'}
          sub="Processing time" color="blue" icon={<HiOutlineServerStack size={16} />} />
        <StatCard label="Errors (24h)" value={overview.system_health.errors_24h}
          sub="System errors" color={overview.system_health.errors_24h > 0 ? 'red' : 'green'} icon={<HiOutlineBellAlert size={16} />} />
        <StatCard label="Unread Alerts" value={overview.alerts.unread}
          sub="Pending review" color={overview.alerts.unread > 0 ? 'yellow' : 'green'} icon={<HiOutlineBellAlert size={16} />} />
      </div>

      <div className={styles.twoCol}>
        {/* Route Distribution */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Query Route Distribution</span>
          </div>
          <div className={styles.sectionBody}>
            {routeTotal > 0 ? (
              <>
                <div style={{ maxWidth: 260, margin: '0 auto' }}>
                  <Doughnut data={doughnutData} options={{
                    responsive: true,
                    plugins: { legend: { position: 'bottom', labels: { color: '#94b3d0', padding: 16, font: { size: 12 } } } },
                    cutout: '60%',
                  }} />
                </div>
                <div className={styles.distBar} style={{ marginTop: 16 }}>
                  {Object.entries(routeDist).map(([route, count]) => (
                    <div
                      key={route}
                      className={styles.distSegment}
                      style={{ width: `${(count / routeTotal) * 100}%`, background: ROUTE_COLORS[route] || '#5e7f9e' }}
                    />
                  ))}
                </div>
                <div className={styles.distLegend}>
                  {Object.entries(routeDist).map(([route, count]) => (
                    <div key={route} className={styles.distLegendItem}>
                      <span className={styles.distDot} style={{ background: ROUTE_COLORS[route] || '#5e7f9e' }} />
                      {route}: {count} ({Math.round((count / routeTotal) * 100)}%)
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className={styles.emptyState}>No queries yet</div>
            )}
          </div>
        </div>

        {/* Document Status */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Document Status</span>
          </div>
          <div className={styles.sectionBody}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {Object.entries(overview.documents.by_status).map(([status, count]) => (
                <div key={status} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{status}</span>
                  <span className={`${styles.badge} ${status === 'completed' ? styles.badgeGreen : status === 'failed' ? styles.badgeRed : styles.badgeYellow}`}>{count}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 20, borderTop: '1px solid var(--border-subtle)', paddingTop: 16 }}>
              <div className={styles.detailLabel}>Embedding Status</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                {Object.entries(overview.documents.by_embedding).map(([status, count]) => (
                  <div key={status} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{status.replace('_', ' ')}</span>
                    <span className={`${styles.badge} ${status === 'completed' ? styles.badgeGreen : status === 'failed' ? styles.badgeRed : styles.badgeGray}`}>{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Recent Activity</span>
        </div>
        <div className={styles.sectionBodyFlush}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Query</th>
                <th>Route</th>
                <th>Agent</th>
                <th>Time</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {overview.recent_activity.map((item) => (
                <tr key={item.id}>
                  <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.query}
                  </td>
                  <td>
                    <span className={`${styles.badge} ${styles.badgeBlue}`}>{item.route || '—'}</span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{item.agent_used || '—'}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
                    {item.processing_time ? `${item.processing_time.toFixed(1)}s` : '—'}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
                    {formatTime(item.timestamp)}
                  </td>
                </tr>
              ))}
              {overview.recent_activity.length === 0 && (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No activity yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// STAT CARD
// ═════════════════════════════════════════════════════════════════════════════

const StatCard: FC<{
  label: string;
  value: string | number;
  sub?: string;
  color: 'blue' | 'green' | 'yellow' | 'red';
  icon: React.ReactNode;
}> = ({ label, value, sub, color, icon }) => {
  const iconClass = {
    blue: styles.statIconBlue,
    green: styles.statIconGreen,
    yellow: styles.statIconYellow,
    red: styles.statIconRed,
  }[color];

  return (
    <div className={styles.statCard}>
      <div className={styles.statHeader}>
        <span className={styles.statLabel}>{label}</span>
        <div className={`${styles.statIcon} ${iconClass}`}>{icon}</div>
      </div>
      <div className={styles.statValue}>{value}</div>
      {sub && <div className={styles.statSub}>{sub}</div>}
    </div>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// QUERY MONITOR TAB
// ═════════════════════════════════════════════════════════════════════════════

const QueryMonitorTab: FC = () => {
  const [queries, setQueries] = useState<QueryLogEntry[]>([]);
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 25, total_pages: 0 });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ route: '', feedback: '', search: '', days: '30' });
  const [selectedQuery, setSelectedQuery] = useState<QueryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(page), days: filters.days };
      if (filters.route) params.route = filters.route;
      if (filters.feedback) params.feedback = filters.feedback;
      if (filters.search) params.search = filters.search;
      const data = await fetchQueryLogs(params);
      setQueries(data.results);
      setPagination({ total: data.total, page: data.page, page_size: data.page_size, total_pages: data.total_pages });
    } catch (e) {
      console.error('Failed to load queries', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const openDetail = async (messageId: string) => {
    setDetailLoading(true);
    try {
      const detail = await fetchQueryDetail(messageId);
      setSelectedQuery(detail);
    } catch (e) {
      console.error('Failed to load query detail', e);
    } finally {
      setDetailLoading(false);
    }
  };

  return (
    <>
      <div className={styles.filterBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search queries..."
          value={filters.search}
          onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <select className={styles.filterSelect} value={filters.route} onChange={(e) => setFilters(f => ({ ...f, route: e.target.value }))}>
          <option value="">All Routes</option>
          <option value="rag">RAG</option>
          <option value="graph">Graph</option>
          <option value="diagnosis">Diagnosis</option>
          <option value="internet">Internet</option>
          <option value="hybrid">Hybrid</option>
        </select>
        <select className={styles.filterSelect} value={filters.feedback} onChange={(e) => setFilters(f => ({ ...f, feedback: e.target.value }))}>
          <option value="">All Feedback</option>
          <option value="correct">Correct</option>
          <option value="incorrect">Incorrect</option>
          <option value="partial">Partial</option>
        </select>
        <select className={styles.filterSelect} value={filters.days} onChange={(e) => setFilters(f => ({ ...f, days: e.target.value }))}>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
          <option value="365">Last year</option>
        </select>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionBodyFlush}>
          {loading ? (
            <div className={styles.loading}><div className={styles.spinner} /> Loading queries...</div>
          ) : (
            <>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Query</th>
                    <th>Route</th>
                    <th>Agent</th>
                    <th>Time</th>
                    <th>Feedback</th>
                    <th>Date</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {queries.map((q) => (
                    <tr key={q.id} className={styles.clickableRow} onClick={() => openDetail(q.id)}>
                      <td style={{ maxWidth: 350, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {q.query}
                      </td>
                      <td><span className={`${styles.badge} ${styles.badgeBlue}`}>{q.route || '—'}</span></td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>{q.agent_used || '—'}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
                        {q.processing_time ? `${q.processing_time.toFixed(1)}s` : '—'}
                      </td>
                      <td>
                        {q.feedback ? (
                          <span className={`${styles.badge} ${q.feedback === 'correct' ? styles.badgeGreen : q.feedback === 'incorrect' ? styles.badgeRed : styles.badgeYellow}`}>
                            {q.feedback}
                          </span>
                        ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>
                        {formatTime(q.timestamp)}
                      </td>
                      <td>
                        {q.has_graph && <span className={`${styles.badge} ${styles.badgeGreen}`} style={{ marginRight: 4 }}>📊</span>}
                        {q.has_diagnosis && <span className={`${styles.badge} ${styles.badgeYellow}`}>🔧</span>}
                      </td>
                    </tr>
                  ))}
                  {queries.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No queries found</td></tr>
                  )}
                </tbody>
              </table>
              <Pagination page={pagination.page} totalPages={pagination.total_pages} total={pagination.total} onPageChange={(p) => load(p)} />
            </>
          )}
        </div>
      </div>

      {/* Detail Modal */}
      {(selectedQuery || detailLoading) && (
        <div className={styles.modalOverlay} onClick={() => !detailLoading && setSelectedQuery(null)}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <span className={styles.modalTitle}>Query Pipeline Detail</span>
              <button className={styles.modalClose} onClick={() => setSelectedQuery(null)}>
                <HiOutlineXMark size={20} />
              </button>
            </div>
            <div className={styles.modalBody}>
              {detailLoading ? (
                <div className={styles.loading}><div className={styles.spinner} /> Loading details...</div>
              ) : selectedQuery ? (
                <>
                  {/* Meta */}
                  <div className={styles.detailMeta}>
                    {selectedQuery.assistant_message && (
                      <>
                        <div className={styles.detailMetaItem}>
                          <span className={styles.detailMetaLabel}>Route</span>
                          <span className={`${styles.badge} ${styles.badgeBlue}`}>{selectedQuery.assistant_message.route}</span>
                        </div>
                        <div className={styles.detailMetaItem}>
                          <span className={styles.detailMetaLabel}>Agent</span>
                          <span className={styles.detailMetaValue}>{selectedQuery.assistant_message.agent_used}</span>
                        </div>
                        <div className={styles.detailMetaItem}>
                          <span className={styles.detailMetaLabel}>Processing Time</span>
                          <span className={styles.detailMetaValue}>
                            {selectedQuery.assistant_message.processing_time
                              ? `${selectedQuery.assistant_message.processing_time.toFixed(2)}s`
                              : 'N/A'}
                          </span>
                        </div>
                        {selectedQuery.assistant_message.feedback && (
                          <div className={styles.detailMetaItem}>
                            <span className={styles.detailMetaLabel}>Feedback</span>
                            <span className={`${styles.badge} ${selectedQuery.assistant_message.feedback === 'correct' ? styles.badgeGreen : styles.badgeRed}`}>
                              {selectedQuery.assistant_message.feedback}
                            </span>
                          </div>
                        )}
                      </>
                    )}
                  </div>

                  {/* User query */}
                  <div className={styles.detailSection}>
                    <div className={styles.detailLabel}>User Query</div>
                    <div className={styles.detailContent}>{selectedQuery.user_message.content}</div>
                  </div>

                  {/* Response */}
                  {selectedQuery.assistant_message && (
                    <div className={styles.detailSection}>
                      <div className={styles.detailLabel}>Assistant Response</div>
                      <div className={styles.detailContent}>{selectedQuery.assistant_message.content}</div>
                    </div>
                  )}

                  {/* Sources */}
                  {selectedQuery.assistant_message?.sources && (
                    <div className={styles.detailSection}>
                      <div className={styles.detailLabel}>Sources</div>
                      <div className={styles.detailContent}>
                        <pre style={{ fontSize: 'var(--text-xs)', overflow: 'auto' }}>
                          {JSON.stringify(selectedQuery.assistant_message.sources, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Pipeline logs */}
                  {selectedQuery.pipeline_logs.length > 0 && (
                    <div className={styles.detailSection}>
                      <div className={styles.detailLabel}>Pipeline Logs ({selectedQuery.pipeline_logs.length})</div>
                      {selectedQuery.pipeline_logs.map((log, i) => (
                        <div key={i} className={styles.pipelineLog}>
                          <span className={styles.logLevel} style={{
                            color: log.level === 'error' || log.level === 'critical' ? 'var(--error)' :
                              log.level === 'warning' ? 'var(--warning)' : 'var(--text-muted)'
                          }}>{log.level}</span>
                          <span className={styles.logCategory}>{log.category}</span>
                          <span className={styles.logMessage}>{log.message}</span>
                          {log.duration_ms && <span className={styles.logTime}>{log.duration_ms}ms</span>}
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// RAG MONITOR TAB
// ═════════════════════════════════════════════════════════════════════════════

const RagMonitorTab: FC = () => {
  const [data, setData] = useState<RagStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ status: '', embedding_status: '', search: '' });
  const [page, setPage] = useState(1);
  const [reindexing, setReindexing] = useState<string | null>(null);

  const load = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(p) };
      if (filters.status) params.status = filters.status;
      if (filters.embedding_status) params.embedding_status = filters.embedding_status;
      if (filters.search) params.search = filters.search;
      const resp = await fetchRagStatus(params);
      setData(resp);
      setPage(p);
    } catch (e) {
      console.error('Failed to load RAG status', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const handleReindex = async (docId: string) => {
    setReindexing(docId);
    try {
      await reindexDocument(docId);
      load(page);
    } catch (e) {
      console.error('Reindex failed', e);
    } finally {
      setReindexing(null);
    }
  };

  return (
    <>
      {/* Aggregates */}
      {data && (
        <div className={styles.statsGrid}>
          <StatCard label="Total Documents" value={data.aggregates.total} color="blue" icon={<HiOutlineDocumentText size={16} />} />
          <StatCard label="Completed" value={data.aggregates.by_status['completed'] || 0} color="green" icon={<HiOutlineDocumentText size={16} />} />
          <StatCard label="Failed" value={data.aggregates.by_status['failed'] || 0} color="red" icon={<HiOutlineDocumentText size={16} />} />
          <StatCard label="Total Chunks" value={data.aggregates.total_chunks} color="blue" icon={<HiOutlineServerStack size={16} />} />
        </div>
      )}

      <div className={styles.filterBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search documents..."
          value={filters.search}
          onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <select className={styles.filterSelect} value={filters.status} onChange={(e) => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
        <select className={styles.filterSelect} value={filters.embedding_status} onChange={(e) => setFilters(f => ({ ...f, embedding_status: e.target.value }))}>
          <option value="">All Embedding</option>
          <option value="not_started">Not Started</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionBodyFlush}>
          {loading ? (
            <div className={styles.loading}><div className={styles.spinner} /> Loading documents...</div>
          ) : (
            <>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Embedding</th>
                    <th>Chunks</th>
                    <th>Uploaded</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((doc) => (
                    <tr key={doc.id}>
                      <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {doc.title}
                      </td>
                      <td><span className={styles.badge} style={{ textTransform: 'uppercase' }}>{doc.file_type}</span></td>
                      <td>
                        <span className={`${styles.badge} ${doc.status === 'completed' ? styles.badgeGreen : doc.status === 'failed' ? styles.badgeRed : styles.badgeYellow}`}>
                          {doc.status}
                        </span>
                      </td>
                      <td>
                        <span className={`${styles.badge} ${doc.embedding_status === 'completed' ? styles.badgeGreen : doc.embedding_status === 'failed' ? styles.badgeRed : styles.badgeGray}`}>
                          {doc.embedding_status.replace('_', ' ')}
                        </span>
                      </td>
                      <td>{doc.total_chunks}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>{formatDate(doc.uploaded_at)}</td>
                      <td>
                        <button
                          className={styles.actionBtn}
                          onClick={() => handleReindex(doc.id)}
                          disabled={reindexing === doc.id || doc.status !== 'completed'}
                        >
                          {reindexing === doc.id ? '...' : 'Re-index'}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {data?.results.length === 0 && (
                    <tr><td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No documents found</td></tr>
                  )}
                </tbody>
              </table>
              {data && <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPageChange={(p) => load(p)} />}
            </>
          )}
        </div>
      </div>
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ANALYTICS MONITOR TAB
// ═════════════════════════════════════════════════════════════════════════════

const AnalyticsMonitorTab: FC = () => {
  const [data, setData] = useState<AnalyticsMonitorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState('30');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetchAnalyticsMonitor({ days });
      setData(resp);
    } catch (e) {
      console.error('Failed to load analytics monitor', e);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (loading && !data) {
    return <div className={styles.loading}><div className={styles.spinner} /> Loading analytics monitor...</div>;
  }
  if (!data) return null;

  return (
    <>
      <div className={styles.statsGrid}>
        <StatCard label="Total Imports" value={data.aggregates.total} color="blue" icon={<HiOutlineChartPie size={16} />} />
        <StatCard label="Total Noon Reports" value={data.aggregates.total_noon_reports} color="green" icon={<HiOutlineChartPie size={16} />} />
        <StatCard label="Graphs Generated" value={data.graph_history.length} sub={`Last ${days} days`} color="blue" icon={<HiOutlineChartBarSquare size={16} />} />
      </div>

      <div className={styles.filterBar}>
        <select className={styles.filterSelect} value={days} onChange={(e) => setDays(e.target.value)}>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </div>

      <div className={styles.twoCol}>
        {/* Import History */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Import History</span>
          </div>
          <div className={styles.sectionBodyFlush}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>File</th>
                  <th>Vessel</th>
                  <th>Status</th>
                  <th>Rows</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {data.imports.map((imp) => (
                  <tr key={imp.id}>
                    <td style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{imp.filename}</td>
                    <td>{imp.vessel}</td>
                    <td>
                      <span className={`${styles.badge} ${imp.status === 'completed' ? styles.badgeGreen : imp.status === 'failed' ? styles.badgeRed : styles.badgeYellow}`}>
                        {imp.status}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--success)' }}>{imp.successful_rows}</span>
                      {imp.failed_rows > 0 && <span style={{ color: 'var(--error)', marginLeft: 4 }}>/ {imp.failed_rows} err</span>}
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>{formatDate(imp.created_at)}</td>
                  </tr>
                ))}
                {data.imports.length === 0 && (
                  <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>No imports</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Top Metrics */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Most Requested Metrics</span>
          </div>
          <div className={styles.sectionBody}>
            {data.top_metrics.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {data.top_metrics.map((m, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{m.metric}</span>
                    <span className={`${styles.badge} ${styles.badgeBlue}`}>{m.count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>No graph metrics recorded yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Graph Generation History */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Graph Generation History</span>
        </div>
        <div className={styles.sectionBodyFlush}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Query</th>
                <th>Chart Type</th>
                <th>Title</th>
                <th>Time</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {data.graph_history.map((g) => (
                <tr key={g.id}>
                  <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{g.query}</td>
                  <td><span className={`${styles.badge} ${styles.badgeGreen}`}>{g.chart_type || 'chart'}</span></td>
                  <td style={{ color: 'var(--text-muted)' }}>{g.title}</td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
                    {g.processing_time ? `${g.processing_time.toFixed(1)}s` : '—'}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>{formatTime(g.timestamp)}</td>
                </tr>
              ))}
              {data.graph_history.length === 0 && (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 24 }}>No graphs generated</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// DIAGNOSIS MONITOR TAB
// ═════════════════════════════════════════════════════════════════════════════

const DiagnosisMonitorTab: FC = () => {
  const [data, setData] = useState<DiagnosisMonitorResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState('30');

  const load = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const resp = await fetchDiagnosisMonitor({ days, page: String(page) });
      setData(resp);
    } catch (e) {
      console.error('Failed to load diagnosis monitor', e);
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (loading && !data) {
    return <div className={styles.loading}><div className={styles.spinner} /> Loading diagnosis monitor...</div>;
  }
  if (!data) return null;

  const feedbackTotal = (data.feedback_stats.correct || 0) + (data.feedback_stats.incorrect || 0) + (data.feedback_stats.partial || 0);

  return (
    <>
      <div className={styles.statsGrid}>
        <StatCard label="Total Diagnoses" value={data.feedback_stats.total || 0} color="blue" icon={<HiOutlineWrenchScrewdriver size={16} />} />
        <StatCard label="Correct" value={data.feedback_stats.correct || 0} color="green" icon={<HiOutlineWrenchScrewdriver size={16} />} />
        <StatCard label="Incorrect" value={data.feedback_stats.incorrect || 0} color="red" icon={<HiOutlineWrenchScrewdriver size={16} />} />
        <StatCard label="Accuracy" value={feedbackTotal > 0 ? `${Math.round(((data.feedback_stats.correct || 0) / feedbackTotal) * 100)}%` : 'N/A'}
          sub={`${feedbackTotal} rated`} color="green" icon={<HiOutlineChartBarSquare size={16} />} />
      </div>

      <div className={styles.filterBar}>
        <select className={styles.filterSelect} value={days} onChange={(e) => setDays(e.target.value)}>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
        </select>
      </div>

      <div className={styles.twoCol}>
        {/* Severity Distribution */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Severity Distribution</span>
          </div>
          <div className={styles.sectionBody}>
            {Object.entries(data.severity_distribution).length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {Object.entries(data.severity_distribution).map(([sev, count]) => (
                  <div key={sev} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span className={`${styles.badge} ${styles[SEVERITY_BADGE[sev] || 'badgeGray']}`}>{sev}</span>
                    <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>No severity data</div>
            )}
          </div>
        </div>

        {/* Feedback Breakdown */}
        <div className={styles.section}>
          <div className={styles.sectionHeader}>
            <span className={styles.sectionTitle}>Feedback Breakdown</span>
          </div>
          <div className={styles.sectionBody}>
            {feedbackTotal > 0 ? (
              <>
                <div className={styles.distBar}>
                  <div className={styles.distSegment} style={{ width: `${((data.feedback_stats.correct || 0) / feedbackTotal) * 100}%`, background: 'var(--success)' }} />
                  <div className={styles.distSegment} style={{ width: `${((data.feedback_stats.partial || 0) / feedbackTotal) * 100}%`, background: 'var(--warning)' }} />
                  <div className={styles.distSegment} style={{ width: `${((data.feedback_stats.incorrect || 0) / feedbackTotal) * 100}%`, background: 'var(--error)' }} />
                </div>
                <div className={styles.distLegend}>
                  <div className={styles.distLegendItem}><span className={styles.distDot} style={{ background: 'var(--success)' }} />Correct: {data.feedback_stats.correct || 0}</div>
                  <div className={styles.distLegendItem}><span className={styles.distDot} style={{ background: 'var(--warning)' }} />Partial: {data.feedback_stats.partial || 0}</div>
                  <div className={styles.distLegendItem}><span className={styles.distDot} style={{ background: 'var(--error)' }} />Incorrect: {data.feedback_stats.incorrect || 0}</div>
                </div>
              </>
            ) : (
              <div className={styles.emptyState}>No feedback data yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Diagnosis list */}
      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <span className={styles.sectionTitle}>Diagnosis History</span>
        </div>
        <div className={styles.sectionBodyFlush}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Query</th>
                <th>Severity</th>
                <th>Category</th>
                <th>Components</th>
                <th>Feedback</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((d) => (
                <tr key={d.id}>
                  <td style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.query}</td>
                  <td>
                    <span className={`${styles.badge} ${styles[SEVERITY_BADGE[d.severity] || 'badgeGray']}`}>{d.severity}</span>
                  </td>
                  <td style={{ color: 'var(--text-muted)' }}>{d.category}</td>
                  <td style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {d.affected_components.slice(0, 3).join(', ')}
                  </td>
                  <td>
                    {d.feedback ? (
                      <span className={`${styles.badge} ${d.feedback === 'correct' ? styles.badgeGreen : d.feedback === 'incorrect' ? styles.badgeRed : styles.badgeYellow}`}>
                        {d.feedback}
                      </span>
                    ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>{formatTime(d.timestamp)}</td>
                </tr>
              ))}
              {data.results.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No diagnoses found</td></tr>
              )}
            </tbody>
          </table>
          <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPageChange={(p) => load(p)} />
        </div>
      </div>
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// SYSTEM LOGS TAB
// ═════════════════════════════════════════════════════════════════════════════

const SystemLogsTab: FC = () => {
  const [data, setData] = useState<SystemLogsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ level: '', category: '', search: '', days: '7' });

  const load = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(page), days: filters.days };
      if (filters.level) params.level = filters.level;
      if (filters.category) params.category = filters.category;
      if (filters.search) params.search = filters.search;
      const resp = await fetchSystemLogs(params);
      setData(resp);
    } catch (e) {
      console.error('Failed to load system logs', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  return (
    <>
      {data && (
        <div className={styles.statsGrid}>
          <StatCard label="Errors (24h)" value={data.aggregates.errors_24h} color={data.aggregates.errors_24h > 0 ? 'red' : 'green'} icon={<HiOutlineServerStack size={16} />} />
          <StatCard label="Warnings (24h)" value={data.aggregates.warnings_24h} color={data.aggregates.warnings_24h > 0 ? 'yellow' : 'green'} icon={<HiOutlineServerStack size={16} />} />
          <StatCard label="Errors (7d)" value={data.aggregates.errors_7d} color={data.aggregates.errors_7d > 0 ? 'red' : 'green'} icon={<HiOutlineServerStack size={16} />} />
        </div>
      )}

      <div className={styles.filterBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder="Search logs..."
          value={filters.search}
          onChange={(e) => setFilters(f => ({ ...f, search: e.target.value }))}
          onKeyDown={(e) => e.key === 'Enter' && load()}
        />
        <select className={styles.filterSelect} value={filters.level} onChange={(e) => setFilters(f => ({ ...f, level: e.target.value }))}>
          <option value="">All Levels</option>
          <option value="debug">Debug</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="critical">Critical</option>
        </select>
        <select className={styles.filterSelect} value={filters.category} onChange={(e) => setFilters(f => ({ ...f, category: e.target.value }))}>
          <option value="">All Categories</option>
          <option value="ingestion">Ingestion</option>
          <option value="indexing">Indexing</option>
          <option value="query_pipeline">Query Pipeline</option>
          <option value="guardrails">Guardrails</option>
          <option value="routing">Routing</option>
          <option value="rag">RAG</option>
          <option value="search">Search</option>
          <option value="reranking">Reranking</option>
          <option value="llm">LLM</option>
          <option value="auth">Auth</option>
          <option value="system">System</option>
        </select>
        <select className={styles.filterSelect} value={filters.days} onChange={(e) => setFilters(f => ({ ...f, days: e.target.value }))}>
          <option value="1">Last 24 hours</option>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
        </select>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionBodyFlush}>
          {loading ? (
            <div className={styles.loading}><div className={styles.spinner} /> Loading logs...</div>
          ) : (
            <>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Level</th>
                    <th>Category</th>
                    <th>Message</th>
                    <th>Duration</th>
                    <th>User</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {data?.results.map((log) => (
                    <tr key={log.id}>
                      <td>
                        <span className={`${styles.badge} ${log.level === 'error' || log.level === 'critical' ? styles.badgeRed : log.level === 'warning' ? styles.badgeYellow : log.level === 'info' ? styles.badgeBlue : styles.badgeGray}`}>
                          {log.level}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-accent)', fontSize: 'var(--text-xs)' }}>{log.category}</td>
                      <td style={{ maxWidth: 400, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.message}
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>
                        {log.duration_ms ? `${log.duration_ms}ms` : '—'}
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>{log.user || '—'}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>
                        {formatTime(log.created_at)}
                      </td>
                    </tr>
                  ))}
                  {data?.results.length === 0 && (
                    <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No logs found</td></tr>
                  )}
                </tbody>
              </table>
              {data && <Pagination page={data.page} totalPages={data.total_pages} total={data.total} onPageChange={(p) => load(p)} />}
            </>
          )}
        </div>
      </div>
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// ALERTS TAB
// ═════════════════════════════════════════════════════════════════════════════

const AlertsTab: FC<{ onUpdate: () => void }> = ({ onUpdate }) => {
  const [alerts, setAlerts] = useState<AlertEntry[]>([]);
  const [pagination, setPagination] = useState({ total: 0, page: 1, page_size: 25, total_pages: 0 });
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ severity: '', type: '', is_read: '' });

  const load = useCallback(async (page = 1) => {
    setLoading(true);
    try {
      const params: Record<string, string> = { page: String(page) };
      if (filters.severity) params.severity = filters.severity;
      if (filters.type) params.type = filters.type;
      if (filters.is_read) params.is_read = filters.is_read;
      const data = await fetchAlerts(params);
      setAlerts(data.results);
      setPagination({ total: data.total, page: data.page, page_size: data.page_size, total_pages: data.total_pages });
    } catch (e) {
      console.error('Failed to load alerts', e);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const handleMarkRead = async (id: string) => {
    await markAlertRead(id);
    load(pagination.page);
    onUpdate();
  };

  const handleMarkAllRead = async () => {
    await markAllAlertsRead();
    load(pagination.page);
    onUpdate();
  };

  return (
    <>
      <div className={styles.filterBar}>
        <select className={styles.filterSelect} value={filters.severity} onChange={(e) => setFilters(f => ({ ...f, severity: e.target.value }))}>
          <option value="">All Severity</option>
          <option value="info">Info</option>
          <option value="warning">Warning</option>
          <option value="error">Error</option>
          <option value="critical">Critical</option>
        </select>
        <select className={styles.filterSelect} value={filters.type} onChange={(e) => setFilters(f => ({ ...f, type: e.target.value }))}>
          <option value="">All Types</option>
          <option value="performance">Performance</option>
          <option value="system">System</option>
          <option value="ingestion">Ingestion</option>
          <option value="fuel">Fuel</option>
          <option value="query">Query</option>
        </select>
        <select className={styles.filterSelect} value={filters.is_read} onChange={(e) => setFilters(f => ({ ...f, is_read: e.target.value }))}>
          <option value="">All</option>
          <option value="false">Unread</option>
          <option value="true">Read</option>
        </select>
        <button className={styles.actionBtn} onClick={handleMarkAllRead}>
          Mark all read
        </button>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionBodyFlush}>
          {loading ? (
            <div className={styles.loading}><div className={styles.spinner} /> Loading alerts...</div>
          ) : (
            <>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Type</th>
                    <th>Title</th>
                    <th>Vessel</th>
                    <th>Date</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((alert) => (
                    <tr key={alert.id} style={{ opacity: alert.is_read ? 0.6 : 1 }}>
                      <td>
                        <span className={`${styles.badge} ${styles[SEVERITY_BADGE[alert.severity] || 'badgeGray']}`}>
                          {alert.severity}
                        </span>
                      </td>
                      <td style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{alert.alert_type}</td>
                      <td>
                        <div style={{ fontWeight: alert.is_read ? 400 : 600 }}>{alert.title}</div>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 2, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {alert.message}
                        </div>
                      </td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>{alert.vessel_name || '—'}</td>
                      <td style={{ color: 'var(--text-muted)', fontSize: 'var(--text-xs)', whiteSpace: 'nowrap' }}>{formatTime(alert.created_at)}</td>
                      <td>
                        {!alert.is_read && (
                          <button className={styles.actionBtn} onClick={() => handleMarkRead(alert.id)}>
                            Mark read
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {alerts.length === 0 && (
                    <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>No alerts</td></tr>
                  )}
                </tbody>
              </table>
              <Pagination page={pagination.page} totalPages={pagination.total_pages} total={pagination.total} onPageChange={(p) => load(p)} />
            </>
          )}
        </div>
      </div>
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// VESSEL PERFORMANCE TAB
// ═════════════════════════════════════════════════════════════════════════════

const VesselPerformanceTab: FC = () => {
  const [vessels, setVessels] = useState<SimpleVessel[]>([]);
  const [selectedVessel, setSelectedVessel] = useState<string>('');
  const [perfData, setPerfData] = useState<VesselPerformanceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState('30');

  useEffect(() => {
    fetchDashboardVessels().then(setVessels).catch(console.error);
  }, []);

  const loadPerformance = useCallback(async () => {
    if (!selectedVessel) return;
    setLoading(true);
    try {
      const data = await fetchVesselPerformance(selectedVessel, { days });
      setPerfData(data);
    } catch (e) {
      console.error('Failed to load vessel performance', e);
    } finally {
      setLoading(false);
    }
  }, [selectedVessel, days]);

  useEffect(() => { loadPerformance(); }, [loadPerformance]);

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#94b3d0', font: { size: 12 } } },
      tooltip: { backgroundColor: '#1a3050', borderColor: '#1e3f6e', borderWidth: 1 },
    },
    scales: {
      x: { ticks: { color: '#5e7f9e', font: { size: 10 } }, grid: { color: '#172e50' } },
      y: { ticks: { color: '#5e7f9e', font: { size: 10 } }, grid: { color: '#172e50' } },
    },
  };

  return (
    <>
      <div className={styles.filterBar}>
        <select
          className={styles.vesselSelect}
          value={selectedVessel}
          onChange={(e) => setSelectedVessel(e.target.value)}
        >
          <option value="">Select a vessel...</option>
          {vessels.map((v) => (
            <option key={v.id} value={v.id}>{v.name} ({v.imo_number})</option>
          ))}
        </select>
        <select className={styles.filterSelect} value={days} onChange={(e) => setDays(e.target.value)}>
          <option value="7">Last 7 days</option>
          <option value="30">Last 30 days</option>
          <option value="90">Last 90 days</option>
          <option value="180">Last 6 months</option>
          <option value="365">Last year</option>
        </select>
      </div>

      {!selectedVessel && (
        <div className={styles.emptyState}>
          <HiOutlineTruck size={48} className={styles.emptyIcon} />
          <span>Select a vessel to view performance data</span>
        </div>
      )}

      {loading && (
        <div className={styles.loading}><div className={styles.spinner} /> Loading performance data...</div>
      )}

      {perfData && !loading && (
        <>
          {/* Summary Stats */}
          <div className={styles.statsGrid}>
            <StatCard label="Avg Speed" value={perfData.summary.avg_speed ? `${perfData.summary.avg_speed} kn` : 'N/A'} color="blue" icon={<HiOutlineTruck size={16} />} />
            <StatCard label="Avg RPM" value={perfData.summary.avg_rpm ?? 'N/A'} color="green" icon={<HiOutlineChartBarSquare size={16} />} />
            <StatCard label="Avg Fuel/Day" value={perfData.summary.avg_fuel ? `${perfData.summary.avg_fuel} MT` : 'N/A'} color="yellow" icon={<HiOutlineChartPie size={16} />} />
            <StatCard label="Total Distance" value={perfData.summary.total_distance ? `${perfData.summary.total_distance} NM` : 'N/A'} color="blue" icon={<HiOutlineTruck size={16} />} />
            <StatCard label="Total Fuel" value={perfData.summary.total_fuel ? `${perfData.summary.total_fuel} MT` : 'N/A'} color="yellow" icon={<HiOutlineChartPie size={16} />} />
            <StatCard label="Reports" value={perfData.summary.report_count} sub={`${perfData.period.from} — ${perfData.period.to}`} color="blue" icon={<HiOutlineChartBarSquare size={16} />} />
          </div>

          {/* Charts */}
          {perfData.trends.dates.length > 0 ? (
            <div className={styles.chartRow}>
              {/* Fuel Trend */}
              <div className={styles.section}>
                <div className={styles.sectionHeader}>
                  <span className={styles.sectionTitle}>Fuel Consumption Trend</span>
                </div>
                <div className={styles.sectionBody}>
                  <div className={styles.chartContainer}>
                    <Line
                      data={{
                        labels: perfData.trends.dates,
                        datasets: [{
                          label: 'Fuel Oil (MT)',
                          data: perfData.trends.fuel,
                          borderColor: '#fbbf24',
                          backgroundColor: 'rgba(251, 191, 36, 0.1)',
                          fill: true,
                          tension: 0.3,
                          pointRadius: 3,
                        }],
                      }}
                      options={chartOptions}
                    />
                  </div>
                </div>
              </div>

              {/* Speed Trend */}
              <div className={styles.section}>
                <div className={styles.sectionHeader}>
                  <span className={styles.sectionTitle}>Speed Trend</span>
                </div>
                <div className={styles.sectionBody}>
                  <div className={styles.chartContainer}>
                    <Line
                      data={{
                        labels: perfData.trends.dates,
                        datasets: [{
                          label: 'Speed (knots)',
                          data: perfData.trends.speed,
                          borderColor: '#00b4d8',
                          backgroundColor: 'rgba(0, 180, 216, 0.1)',
                          fill: true,
                          tension: 0.3,
                          pointRadius: 3,
                        }],
                      }}
                      options={chartOptions}
                    />
                  </div>
                </div>
              </div>

              {/* RPM Trend */}
              <div className={styles.section}>
                <div className={styles.sectionHeader}>
                  <span className={styles.sectionTitle}>RPM Trend</span>
                </div>
                <div className={styles.sectionBody}>
                  <div className={styles.chartContainer}>
                    <Line
                      data={{
                        labels: perfData.trends.dates,
                        datasets: [{
                          label: 'RPM',
                          data: perfData.trends.rpm,
                          borderColor: '#34d399',
                          backgroundColor: 'rgba(52, 211, 153, 0.1)',
                          fill: true,
                          tension: 0.3,
                          pointRadius: 3,
                        }],
                      }}
                      options={chartOptions}
                    />
                  </div>
                </div>
              </div>

              {/* Distance */}
              <div className={styles.section}>
                <div className={styles.sectionHeader}>
                  <span className={styles.sectionTitle}>Distance Sailed</span>
                </div>
                <div className={styles.sectionBody}>
                  <div className={styles.chartContainer}>
                    <Bar
                      data={{
                        labels: perfData.trends.dates,
                        datasets: [{
                          label: 'Distance (NM)',
                          data: perfData.trends.distance,
                          backgroundColor: 'rgba(0, 180, 216, 0.5)',
                          borderColor: '#00b4d8',
                          borderWidth: 1,
                        }],
                      }}
                      options={chartOptions}
                    />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className={styles.emptyState}>
              <HiOutlineChartBarSquare size={48} className={styles.emptyIcon} />
              <span>No data available for the selected period</span>
            </div>
          )}
        </>
      )}
    </>
  );
};

// ═════════════════════════════════════════════════════════════════════════════
// PAGINATION COMPONENT
// ═════════════════════════════════════════════════════════════════════════════

const Pagination: FC<{
  page: number;
  totalPages: number;
  total: number;
  onPageChange: (page: number) => void;
}> = ({ page, totalPages, total, onPageChange }) => {
  if (totalPages <= 1) return null;

  return (
    <div className={styles.pagination}>
      <button disabled={page <= 1} onClick={() => onPageChange(page - 1)}>Previous</button>
      <span className={styles.pageInfo}>
        Page {page} of {totalPages} ({total} total)
      </span>
      <button disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Next</button>
    </div>
  );
};

export default DashboardPage;
