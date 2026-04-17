import { type FC, type FormEvent, useState, useEffect, useCallback, useRef } from 'react';
import { fetchVessels, fetchNoonReports, createNoonReport, deleteNoonReport, exportNoonReportsCsv, downloadNoonReportTemplate, importNoonReportsCsv } from '@/api';
import type { Vessel, NoonReport, NoonReportCreatePayload } from '@/types';
import { formatDate } from '@/utils';
import {
  HiOutlinePlus,
  HiOutlineXMark,
  HiOutlineTrash,
  HiOutlineArrowPath,
  HiOutlineClipboardDocumentList,
  HiOutlineArrowDownTray,
  HiOutlineArrowUpTray,
} from 'react-icons/hi2';
import toast, { Toaster } from 'react-hot-toast';
import styles from './NoonReportsPage.module.css';

const EMPTY_FORM: NoonReportCreatePayload = {
  report_date: new Date().toISOString().split('T')[0],
  report_time: '12:00',
  voyage_number: '',
  latitude: null,
  longitude: null,
  speed_avg: null,
  speed_ordered: null,
  distance_sailed: null,
  rpm_avg: null,
  fo_consumption: null,
  bf_consumption: null,
  wind_force: null,
  sea_state: null,
  cargo_condition: '',
  remarks: '',
};

const NoonReportsPage: FC = () => {
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [selectedVessel, setSelectedVessel] = useState<string>('');
  const [reports, setReports] = useState<NoonReport[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NoonReportCreatePayload>({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  // Load vessels on mount
  useEffect(() => {
    fetchVessels().then((data) => {
      setVessels(data);
      if (data.length > 0) setSelectedVessel(data[0].id);
    }).catch(() => setError('Failed to load vessels'));
  }, []);

  const loadReports = useCallback(async () => {
    if (!selectedVessel) return;
    setIsLoading(true);
    try {
      const data = await fetchNoonReports(selectedVessel);
      setReports(data.results);
      setTotal(data.total);
    } catch {
      setError('Failed to load noon reports');
    } finally {
      setIsLoading(false);
    }
  }, [selectedVessel]);

  useEffect(() => { void loadReports(); }, [loadReports]);

  const handleChange = (field: keyof NoonReportCreatePayload, value: string | number | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedVessel || !form.report_date) return;
    setSubmitting(true);
    setError(null);
    try {
      await createNoonReport(selectedVessel, form);
      toast.success('Noon report created successfully!', {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
      });
      setForm({ ...EMPTY_FORM });
      setShowForm(false);
      await loadReports();
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const resp = (err as {
          response: {
            status?: number;
            data?: { errors?: Record<string, string[]>; error?: string; detail?: string };
          };
        }).response;
        const errs = resp?.data?.errors;
        if (errs) {
          const messages = Object.entries(errs).map(([k, v]) => `${k}: ${v.join(', ')}`).join('; ');
          setError(messages);
        } else if (resp?.data?.error || resp?.data?.detail) {
          setError(resp.data.error ?? resp.data.detail ?? 'Failed to create noon report');
        } else if (resp?.status === 401) {
          setError('Your session has expired. Please login again and retry.');
        } else {
          setError('Failed to create noon report');
        }
      } else {
        setError('Failed to create noon report');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (report: NoonReport) => {
    if (!window.confirm(`Delete noon report from ${report.report_date}?`)) return;
    setDeletingId(report.id);
    setError(null);
    try {
      await deleteNoonReport(selectedVessel, report.id);
      toast.success('Noon report deleted.', {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
      });
      await loadReports();
    } catch {
      setError('Failed to delete noon report');
    } finally {
      setDeletingId(null);
    }
  };

  const handleExport = async () => {
    if (!selectedVessel) return;
    const vessel = vessels.find((v) => v.id === selectedVessel);
    try {
      await exportNoonReportsCsv(selectedVessel, vessel?.name ?? 'vessel');
      toast.success('Noon reports exported!', {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
      });
    } catch {
      setError('Failed to export noon reports');
    }
  };

  const handleTemplate = async () => {
    try {
      await downloadNoonReportTemplate();
    } catch {
      setError('Failed to download template');
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedVessel) return;
    setImporting(true);
    setError(null);
    try {
      const result = await importNoonReportsCsv(selectedVessel, file);
      toast.success(`Imported ${result.created} report(s), ${result.skipped} skipped.`, {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
        duration: 5000,
      });
      if (result.errors.length > 0) {
        setError(`Import warnings: ${result.errors.join('; ')}`);
      }
      await loadReports();
    } catch {
      setError('Failed to import noon reports');
    } finally {
      setImporting(false);
      if (importRef.current) importRef.current.value = '';
    }
  };

  const numField = (label: string, field: keyof NoonReportCreatePayload, placeholder?: string, step?: string) => (
    <div className={styles.field}>
      <label>{label}</label>
      <input
        type="number"
        step={step ?? 'any'}
        value={(form[field] as number | null) ?? ''}
        onChange={(e) => handleChange(field, e.target.value ? Number(e.target.value) : null)}
        placeholder={placeholder}
      />
    </div>
  );

  return (
    <div className={styles.page}>
      <Toaster position="top-right" />
      <div className={styles.topbar}>
        <h1 className={styles.title}>Noon Reports</h1>
        <div className={styles.topActions}>
          <select
            className={styles.vesselSelect}
            value={selectedVessel}
            onChange={(e) => setSelectedVessel(e.target.value)}
          >
            {vessels.length === 0 && <option value="">No vessels</option>}
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>{v.name}</option>
            ))}
          </select>
          <button className={styles.refreshBtn} onClick={() => void handleExport()} disabled={!selectedVessel} title="Export CSV">
            <HiOutlineArrowDownTray size={16} />
            <span className={styles.refreshText}>Export CSV</span>
          </button>
          <button className={styles.refreshBtn} onClick={() => void handleTemplate()} title="Download Template">
            <HiOutlineArrowDownTray size={16} />
            <span className={styles.refreshText}>Template</span>
          </button>
          <button className={styles.refreshBtn} onClick={() => importRef.current?.click()} disabled={!selectedVessel || importing} title="Import CSV">
            <HiOutlineArrowUpTray size={16} />
            <span className={styles.refreshText}>{importing ? 'Importing...' : 'Import CSV'}</span>
          </button>
          <input ref={importRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={(e) => void handleImportFile(e)} />
          <button className={styles.refreshBtn} onClick={() => void loadReports()} title="Refresh">
            <HiOutlineArrowPath size={16} />
            <span className={styles.refreshText}>Refresh</span>
          </button>
          <button
            className={styles.addBtn}
            onClick={() => setShowForm(!showForm)}
            disabled={!selectedVessel}
          >
            {showForm ? <><HiOutlineXMark size={16} /> Cancel</> : <><HiOutlinePlus size={16} /> Add Report</>}
          </button>
        </div>
      </div>

      <div className={styles.content}>
        {error && <div className={styles.error}>{error}</div>}

        {showForm && (
          <form className={styles.form} onSubmit={handleSubmit}>
            <h3 className={styles.formTitle}>Create Noon Report</h3>

            <div className={styles.formSection}>
              <h4 className={styles.sectionTitle}>Report Info</h4>
              <div className={styles.formGrid}>
                <div className={styles.field}>
                  <label>Report Date *</label>
                  <input type="date" value={form.report_date} onChange={(e) => handleChange('report_date', e.target.value)} required />
                </div>
                <div className={styles.field}>
                  <label>Report Time</label>
                  <input type="time" value={form.report_time ?? ''} onChange={(e) => handleChange('report_time', e.target.value)} />
                </div>
                <div className={styles.field}>
                  <label>Voyage Number</label>
                  <input value={form.voyage_number ?? ''} onChange={(e) => handleChange('voyage_number', e.target.value)} placeholder="e.g. V-042" />
                </div>
              </div>
            </div>

            <div className={styles.formSection}>
              <h4 className={styles.sectionTitle}>Position</h4>
              <div className={styles.formGrid}>
                {numField('Latitude', 'latitude', '-90 to 90')}
                {numField('Longitude', 'longitude', '-180 to 180')}
              </div>
            </div>

            <div className={styles.formSection}>
              <h4 className={styles.sectionTitle}>Performance</h4>
              <div className={styles.formGrid}>
                {numField('Avg Speed (knots)', 'speed_avg', '0-35')}
                {numField('Ordered Speed (knots)', 'speed_ordered', '0-35')}
                {numField('Distance Sailed (NM)', 'distance_sailed', '0-999')}
                {numField('Avg RPM', 'rpm_avg', '0-250')}
              </div>
            </div>

            <div className={styles.formSection}>
              <h4 className={styles.sectionTitle}>Fuel Consumption (MT)</h4>
              <div className={styles.formGrid}>
                {numField('FO Consumption', 'fo_consumption', '0-300')}
                {numField('BF Consumption', 'bf_consumption', '0-100')}
              </div>
            </div>

            <div className={styles.formSection}>
              <h4 className={styles.sectionTitle}>Weather & Cargo</h4>
              <div className={styles.formGrid}>
                {numField('Wind Force (BF)', 'wind_force', '0-12', '1')}
                {numField('Sea State (Douglas)', 'sea_state', '0-9', '1')}
                <div className={styles.field}>
                  <label>Cargo Condition</label>
                  <select value={form.cargo_condition ?? ''} onChange={(e) => handleChange('cargo_condition', e.target.value)}>
                    <option value="">— Select —</option>
                    <option value="laden">Laden</option>
                    <option value="ballast">Ballast</option>
                    <option value="part_laden">Part Laden</option>
                  </select>
                </div>
              </div>
            </div>

            <div className={styles.formSection}>
              <h4 className={styles.sectionTitle}>Remarks</h4>
              <textarea
                className={styles.textarea}
                value={form.remarks ?? ''}
                onChange={(e) => handleChange('remarks', e.target.value)}
                placeholder="Any additional notes..."
                rows={3}
              />
            </div>

            <button type="submit" className={styles.submitBtn} disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Noon Report'}
            </button>
          </form>
        )}

        <h3 className={styles.tableTitle}>Noon Reports ({total})</h3>

        {isLoading ? (
          <div className={styles.loading}>
            <div className={styles.loadingSpinner} />
            Loading reports...
          </div>
        ) : reports.length === 0 ? (
          <div className={styles.empty}>
            <HiOutlineClipboardDocumentList size={40} className={styles.emptyIcon} />
            <h3>{selectedVessel ? 'No noon reports for this vessel yet' : 'Select a vessel to view reports'}</h3>
            <p>{selectedVessel ? 'Click "Add Report" to create the first noon report.' : 'Use the vessel selector above to get started.'}</p>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Voyage</th>
                  <th>Speed (kn)</th>
                  <th>RPM</th>
                  <th>Distance (NM)</th>
                  <th>FO (MT)</th>
                  <th>BF (MT)</th>
                  <th>Wind (BF)</th>
                  <th>Sea State</th>
                  <th>Cargo</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => (
                  <tr key={r.id}>
                    <td className={styles.dateCell}>{formatDate(r.report_date)}</td>
                    <td>{r.report_time ?? '—'}</td>
                    <td>{r.voyage_number || '—'}</td>
                    <td>{r.speed_avg ?? '—'}</td>
                    <td>{r.rpm_avg ?? '—'}</td>
                    <td>{r.distance_sailed ?? '—'}</td>
                    <td>{r.fo_consumption ?? '—'}</td>
                    <td>{r.bf_consumption ?? '—'}</td>
                    <td>{r.wind_force ?? '—'}</td>
                    <td>{r.sea_state ?? '—'}</td>
                    <td>{r.cargo_condition || '—'}</td>
                    <td>
                      <button
                        className={styles.deleteBtn}
                        onClick={() => void handleDelete(r)}
                        disabled={deletingId === r.id}
                        title="Delete report"
                      >
                        <HiOutlineTrash size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default NoonReportsPage;
