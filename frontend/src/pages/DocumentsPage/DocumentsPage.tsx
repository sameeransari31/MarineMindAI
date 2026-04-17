import { type FC, type DragEvent, useRef, useState, useCallback } from 'react';
import { useDocuments } from '@/hooks';
import { formatFileSize, formatDate } from '@/utils';
import {
  HiOutlineCloudArrowUp,
  HiOutlineDocument,
  HiOutlineArrowPath,
  HiOutlineDocumentText,
  HiOutlineCheckCircle,
} from 'react-icons/hi2';
import toast, { Toaster } from 'react-hot-toast';
import styles from './DocumentsPage.module.css';

const DocumentsPage: FC = () => {
  const { documents, isLoading, isUploading, isDeleting, error, upload, remove, refresh } = useDocuments();
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFile = useCallback(
    async (file: File) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast.error('Only PDF files are supported.', {
          style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
        });
        return;
      }
      if (file.size > 50 * 1024 * 1024) {
        toast.error('File too large. Maximum 50MB.', {
          style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
        });
        return;
      }
      const success = await upload(file);
      if (success) {
        toast.success(`"${file.name}" uploaded successfully!`, {
          style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-primary)', fontSize: '13px' },
        });
      }
    },
    [upload]
  );

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) void handleFile(file);
    },
    [handleFile]
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) void handleFile(file);
      e.target.value = '';
    },
    [handleFile]
  );

  const statusClass = (status: string) => {
    const map: Record<string, string> = {
      pending: styles.statusPending,
      processing: styles.statusProcessing,
      completed: styles.statusCompleted,
      failed: styles.statusFailed,
    };
    return `${styles.statusBadge} ${map[status] ?? ''}`;
  };

  return (
    <div className={styles.page}>
      <Toaster position="top-right" />
      <div className={styles.topbar}>
        <h1 className={styles.title}>Document Management</h1>
        <button className={styles.refreshBtn} onClick={() => void refresh()} title="Refresh">
          <HiOutlineArrowPath size={16} />
          <span className={styles.refreshText}>Refresh</span>
        </button>
      </div>

      <div className={styles.content}>
        <div className={styles.uploadHeader}>
          <HiOutlineDocument size={24} />
          <div>
            <h2>Upload Ship Manuals & Documents</h2>
            <p>
              Upload PDF documents to build the knowledge base. Documents are
              automatically chunked, embedded, and stored for RAG retrieval.
            </p>
          </div>
        </div>

        <div
          className={`${styles.uploadZone} ${dragOver ? styles.dragOver : ''} ${isUploading ? styles.uploading : ''}`}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          {isUploading ? (
            <>
              <div className={styles.uploadSpinner} />
              <h3>Uploading document...</h3>
              <p>Processing and indexing for AI retrieval</p>
            </>
          ) : (
            <>
              <HiOutlineCloudArrowUp size={48} className={styles.uploadIcon} />
              <h3>Drop PDF here or click to upload</h3>
              <p>Maximum file size: 50MB</p>
            </>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={handleFileInput}
        />

        {error && <div className={styles.error}>{error}</div>}

        <h3 className={styles.tableTitle}>Uploaded Documents</h3>

        {isLoading ? (
          <div className={styles.loading}>
            <div className={styles.loadingSpinner} />
            Loading documents...
          </div>
        ) : documents.length === 0 ? (
          <div className={styles.empty}>
            <HiOutlineDocumentText size={40} className={styles.emptyIcon} />
            <h3>No documents uploaded yet</h3>
            <p>Upload PDF documents to build the AI knowledge base.</p>
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Pages</th>
                  <th>Chunks</th>
                  <th>Status</th>
                  <th>Uploaded</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className={styles.docTitle}>{doc.title}</td>
                    <td>{doc.file_type}</td>
                    <td>{formatFileSize(doc.file_size)}</td>
                    <td>{doc.total_pages ?? '--'}</td>
                    <td>{doc.total_chunks}</td>
                    <td>
                      <span className={statusClass(doc.status)}>{doc.status}</span>
                    </td>
                    <td>{formatDate(doc.uploaded_at)}</td>
                    <td>
                      {confirmId === doc.id ? (
                        <span className={styles.confirmGroup}>
                          <button
                            className={styles.confirmYes}
                            disabled={isDeleting === doc.id}
                            onClick={async () => {
                              await remove(doc.id);
                              setConfirmId(null);
                            }}
                          >
                            {isDeleting === doc.id ? '...' : 'Yes'}
                          </button>
                          <button
                            className={styles.confirmNo}
                            onClick={() => setConfirmId(null)}
                          >
                            No
                          </button>
                        </span>
                      ) : (
                        <button
                          className={styles.deleteBtn}
                          onClick={() => setConfirmId(doc.id)}
                        >
                          Delete
                        </button>
                      )}
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

export default DocumentsPage;
