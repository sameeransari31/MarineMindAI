import { type FC, type FormEvent, useState, useEffect, useCallback, useRef } from 'react';
import { fetchVessels, createVessel, deleteVessel, exportVesselsCsv, downloadVesselTemplate, importVesselsCsv } from '@/api';
import type { Vessel, VesselCreatePayload } from '@/types';
import { HiOutlinePlus, HiOutlineXMark, HiOutlineTrash, HiOutlineArrowPath, HiOutlineTruck, HiOutlineArrowDownTray, HiOutlineArrowUpTray } from 'react-icons/hi2';
import toast, { Toaster } from 'react-hot-toast';
import styles from './VesselsPage.module.css';

const VESSEL_TYPES = [
  { value: 'bulk_carrier', label: 'Bulk Carrier' },
  { value: 'tanker', label: 'Tanker' },
  { value: 'container', label: 'Container Ship' },
  { value: 'lng_carrier', label: 'LNG Carrier' },
  { value: 'lpg_carrier', label: 'LPG Carrier' },
  { value: 'general_cargo', label: 'General Cargo' },
  { value: 'ro_ro', label: 'Ro-Ro' },
  { value: 'passenger', label: 'Passenger Ship' },
  { value: 'offshore', label: 'Offshore Vessel' },
  { value: 'tug', label: 'Tug' },
  { value: 'other', label: 'Other' },
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'in_port', label: 'In Port' },
  { value: 'dry_dock', label: 'Dry Dock' },
  { value: 'laid_up', label: 'Laid Up' },
  { value: 'decommissioned', label: 'Decommissioned' },
];

const EMPTY_FORM: VesselCreatePayload = {
  name: '',
  vessel_type: 'bulk_carrier',
  imo_number: '',
  call_sign: '',
  flag_state: '',
  dwt: null,
  grt: null,
  year_built: null,
  fleet_name: '',
  owner: '',
  manager: '',
  operational_status: 'active',
  main_engine_type: '',
};

const VesselsPage: FC = () => {
  const [vessels, setVessels] = useState<Vessel[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<VesselCreatePayload>({ ...EMPTY_FORM });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const importRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchVessels();
      setVessels(data);
    } catch {
      setError('Failed to load vessels');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const handleChange = (field: keyof VesselCreatePayload, value: string | number | null) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.imo_number.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createVessel(form);
      toast.success(`Vessel "${form.name}" created successfully!`, {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
      });
      setForm({ ...EMPTY_FORM });
      setShowForm(false);
      await refresh();
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
          setError(resp.data.error ?? resp.data.detail ?? 'Failed to create vessel');
        } else if (resp?.status === 401) {
          setError('Your session has expired. Please login again and retry.');
        } else {
          setError('Failed to create vessel');
        }
      } else {
        setError('Failed to create vessel');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const statusColor = (s: string) => {
    const map: Record<string, string> = {
      active: styles.statusActive,
      in_port: styles.statusInPort,
      dry_dock: styles.statusDryDock,
      laid_up: styles.statusLaidUp,
      decommissioned: styles.statusDecommissioned,
    };
    return `${styles.statusBadge} ${map[s] ?? ''}`;
  };

  const handleDelete = async (vessel: Vessel) => {
    if (!window.confirm(`Delete vessel "${vessel.name}"? This will also delete all its noon reports.`)) return;
    setDeletingId(vessel.id);
    setError(null);
    try {
      await deleteVessel(vessel.id);
      toast.success(`Vessel "${vessel.name}" deleted.`, {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
      });
      await refresh();
    } catch {
      setError('Failed to delete vessel');
    } finally {
      setDeletingId(null);
    }
  };

  const handleExport = async () => {
    try {
      await exportVesselsCsv();
      toast.success('Vessels exported!', {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
      });
    } catch {
      setError('Failed to export vessels');
    }
  };

  const handleTemplate = async () => {
    try {
      await downloadVesselTemplate();
    } catch {
      setError('Failed to download template');
    }
  };

  const handleImportFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    setError(null);
    try {
      const result = await importVesselsCsv(file);
      toast.success(`Imported ${result.created} vessel(s), ${result.skipped} skipped.`, {
        style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
        duration: 5000,
      });
      if (result.errors.length > 0) {
        setError(`Import warnings: ${result.errors.join('; ')}`);
      }
      await refresh();
    } catch {
      setError('Failed to import vessels');
    } finally {
      setImporting(false);
      if (importRef.current) importRef.current.value = '';
    }
  };

  return (
    <div className={styles.page}>
      <Toaster position="top-right" />
      <div className={styles.topbar}>
        <h1 className={styles.title}>Vessel Management</h1>
        <div className={styles.topActions}>
          <button className={styles.refreshBtn} onClick={() => void handleExport()} title="Export CSV">
            <HiOutlineArrowDownTray size={16} />
            <span className={styles.refreshText}>Export CSV</span>
          </button>
          <button className={styles.refreshBtn} onClick={() => void handleTemplate()} title="Download Template">
            <HiOutlineArrowDownTray size={16} />
            <span className={styles.refreshText}>Template</span>
          </button>
          <button className={styles.refreshBtn} onClick={() => importRef.current?.click()} disabled={importing} title="Import CSV">
            <HiOutlineArrowUpTray size={16} />
            <span className={styles.refreshText}>{importing ? 'Importing...' : 'Import CSV'}</span>
          </button>
          <input ref={importRef} type="file" accept=".csv" style={{ display: 'none' }} onChange={(e) => void handleImportFile(e)} />
          <button className={styles.refreshBtn} onClick={() => void refresh()} title="Refresh">
            <HiOutlineArrowPath size={16} />
            <span className={styles.refreshText}>Refresh</span>
          </button>
          <button className={styles.addBtn} onClick={() => setShowForm(!showForm)}>
            {showForm ? <><HiOutlineXMark size={16} /> Cancel</> : <><HiOutlinePlus size={16} /> Add Vessel</>}
          </button>
        </div>
      </div>

      <div className={styles.content}>
        {error && <div className={styles.error}>{error}</div>}

        {showForm && (
          <form className={styles.form} onSubmit={handleSubmit}>
            <h3 className={styles.formTitle}>Create New Vessel</h3>
            <div className={styles.formGrid}>
              <div className={styles.field}>
                <label>Vessel Name *</label>
                <input value={form.name} onChange={(e) => handleChange('name', e.target.value)} required />
              </div>
              <div className={styles.field}>
                <label>IMO Number *</label>
                <input value={form.imo_number} onChange={(e) => handleChange('imo_number', e.target.value)} required placeholder="e.g. 9876543" />
              </div>
              <div className={styles.field}>
                <label>Vessel Type</label>
                <select value={form.vessel_type} onChange={(e) => handleChange('vessel_type', e.target.value)}>
                  {VESSEL_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div className={styles.field}>
                <label>Status</label>
                <select value={form.operational_status} onChange={(e) => handleChange('operational_status', e.target.value)}>
                  {STATUS_OPTIONS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
                </select>
              </div>
              <div className={styles.field}>
                <label>Call Sign</label>
                <input value={form.call_sign} onChange={(e) => handleChange('call_sign', e.target.value)} />
              </div>
              <div className={styles.field}>
                <label>Flag State</label>
                <input value={form.flag_state} onChange={(e) => handleChange('flag_state', e.target.value)} />
              </div>
              <div className={styles.field}>
                <label>DWT</label>
                <input type="number" value={form.dwt ?? ''} onChange={(e) => handleChange('dwt', e.target.value ? Number(e.target.value) : null)} />
              </div>
              <div className={styles.field}>
                <label>GRT</label>
                <input type="number" value={form.grt ?? ''} onChange={(e) => handleChange('grt', e.target.value ? Number(e.target.value) : null)} />
              </div>
              <div className={styles.field}>
                <label>Year Built</label>
                <input type="number" value={form.year_built ?? ''} onChange={(e) => handleChange('year_built', e.target.value ? Number(e.target.value) : null)} />
              </div>
              <div className={styles.field}>
                <label>Main Engine Type</label>
                <input value={form.main_engine_type} onChange={(e) => handleChange('main_engine_type', e.target.value)} placeholder="e.g. MAN B&W 6S50MC-C" />
              </div>
              <div className={styles.field}>
                <label>Fleet Name</label>
                <input value={form.fleet_name} onChange={(e) => handleChange('fleet_name', e.target.value)} />
              </div>
              <div className={styles.field}>
                <label>Owner</label>
                <input value={form.owner} onChange={(e) => handleChange('owner', e.target.value)} />
              </div>
            </div>
            <button type="submit" className={styles.submitBtn} disabled={submitting}>
              {submitting ? 'Creating...' : 'Create Vessel'}
            </button>
          </form>
        )}

        <h3 className={styles.tableTitle}>Registered Vessels ({vessels.length})</h3>

        {isLoading ? (
          <div className={styles.loading}>
            <div className={styles.loadingSpinner} />
            Loading vessels...
          </div>
        ) : vessels.length === 0 ? (
          <div className={styles.empty}>
            <HiOutlineTruck size={40} className={styles.emptyIcon} />
            <h3>No vessels registered yet</h3>
            <p>Click "Add Vessel" to register your first vessel.</p>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Vessel Name</th>
                  <th>Type</th>
                  <th>IMO</th>
                  <th>Fleet</th>
                  <th>Status</th>
                  <th>Reports</th>
                  <th>Docs</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {vessels.map((v) => (
                  <tr key={v.id}>
                    <td className={styles.vesselName}>{v.name}</td>
                    <td>{VESSEL_TYPES.find((t) => t.value === v.vessel_type)?.label ?? v.vessel_type}</td>
                    <td>{v.imo_number}</td>
                    <td>{v.fleet_name || '—'}</td>
                    <td><span className={statusColor(v.operational_status)}>{STATUS_OPTIONS.find((s) => s.value === v.operational_status)?.label ?? v.operational_status}</span></td>
                    <td>{v.noon_report_count}</td>
                    <td>{v.document_count}</td>
                    <td>
                      <button
                        className={styles.deleteBtn}
                        onClick={() => void handleDelete(v)}
                        disabled={deletingId === v.id}
                        title="Delete vessel"
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

export default VesselsPage;
