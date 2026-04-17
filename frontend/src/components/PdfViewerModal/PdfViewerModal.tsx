import { type FC, useEffect, useMemo, useState } from 'react';
import {
  HiOutlineDocumentText,
  HiOutlineBookmarkSquare,
  HiOutlineXMark,
} from 'react-icons/hi2';
import type { CitationEntry } from '@/types';
import styles from './PdfViewerModal.module.css';

interface PdfViewerModalProps {
  entry: CitationEntry;
  citationKey: string;
  onClose: () => void;
}

const PdfViewerModal: FC<PdfViewerModalProps> = ({ entry, citationKey, onClose }) => {
  const [pdfAvailable, setPdfAvailable] = useState(true);

  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [onClose]);

  // Build PDF URL with page navigation
  const pdfUrl = useMemo(() => {
    const base = entry.url ?? '';
    if (!base) return '';
    if (!entry.page) return base;
    const joiner = base.includes('#') ? '&' : '#';
    return `${base}${joiner}page=${entry.page}`;
  }, [entry.url, entry.page]);

  useEffect(() => {
    // Reset fallback state when citation changes.
    setPdfAvailable(true);
  }, [pdfUrl, citationKey]);

  const docName = entry.source ?? 'Document';

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.docIcon}>
              <HiOutlineDocumentText size={18} />
            </span>
            <span className={styles.docTitle}>{docName}</span>
            {entry.page && (
              <span className={styles.pageBadge}>Page {entry.page}</span>
            )}
          </div>
          <button className={styles.closeBtn} onClick={onClose} title="Close (Esc)">
            <HiOutlineXMark size={18} />
          </button>
        </div>

        {/* Content: Chunk panel + PDF viewer */}
        <div className={styles.content}>
          {/* Chunk text panel */}
          {entry.chunk_text && (
            <div className={styles.chunkPanel}>
              <div className={styles.chunkHeader}>
                <HiOutlineBookmarkSquare size={14} />
                Cited Content — {citationKey}
              </div>
              <div className={styles.chunkBody}>
                <div className={styles.chunkLabel}>Extracted Chunk</div>
                <div className={styles.chunkText}>{entry.chunk_text}</div>
                <div className={styles.chunkMeta}>
                  {entry.score !== undefined && (
                    <span className={styles.metaTag}>
                      {(entry.score * 100).toFixed(1)}% match
                    </span>
                  )}
                  {entry.chunk_index !== undefined && (
                    <span className={styles.metaTag}>
                      Chunk #{entry.chunk_index}
                    </span>
                  )}
                  {entry.page && (
                    <span className={`${styles.metaTag} ${styles.metaTagGreen}`}>
                      Page {entry.page}
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* PDF Viewer */}
          {pdfUrl && pdfAvailable ? (
            <iframe
              className={styles.pdfFrame}
              src={pdfUrl}
              title={`PDF Viewer — ${docName}`}
              onError={() => setPdfAvailable(false)}
            />
          ) : (
            <div className={styles.noUrl}>
              <HiOutlineDocumentText size={32} />
              <span>PDF preview not available for this document.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PdfViewerModal;
