import { type FC, type ReactNode, useState, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import type {
  ChatMessage as ChatMessageType,
  Source,
  HybridSources,
  CitationMap,
  CitationEntry,
} from '@/types';
import { formatTime } from '@/utils';
import { ChartRenderer } from '@/components/ChartRenderer';
import { DiagnosisCard } from '@/components/DiagnosisCard';
import { FeedbackButtons } from '@/components/FeedbackButtons';
import { PdfViewerModal } from '@/components/PdfViewerModal';
import {
  HiOutlineDocumentText,
  HiOutlineGlobeAlt,
  HiOutlineClipboard,
  HiOutlineCheck,
  HiOutlineChevronDown,
  HiOutlineChevronUp,
  HiOutlineClock,
  HiOutlineCpuChip,
} from 'react-icons/hi2';
import styles from './ChatBubble.module.css';

interface ChatBubbleProps {
  message: ChatMessageType;
}

function isHybridSources(
  sources: Source[] | HybridSources,
): sources is HybridSources {
  return (
    sources !== null &&
    typeof sources === 'object' &&
    !Array.isArray(sources) &&
    ('internal' in sources || 'external' in sources)
  );
}

function citationLabel(entry: CitationEntry): string {
  if (entry.type === 'web') return entry.title ?? entry.url ?? 'Web Source';
  return entry.source ?? 'Document';
}

function isDocumentCitation(entry: CitationEntry): boolean {
  // Be permissive for backward compatibility with older citation payloads
  // that may not include an explicit "type".
  if (entry.type === 'document') return true;
  if (entry.type === 'web') return false;
  return Boolean(entry.document_id || entry.chunk_text || entry.source);
}

/**
 * Replace inline [doc1], [web2] in text with citation markers,
 * then render the rest as Markdown.
 */
function renderContentWithCitations(
  text: string,
  citationMap: CitationMap,
  onDocCitationClick?: (key: string, entry: CitationEntry) => void,
): ReactNode[] {
  const citationPattern = /\[(doc\d+|web\d+)\]/g;
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = citationPattern.exec(text)) !== null) {
    const key = match[1];
    const before = text.slice(lastIndex, match.index);

    if (before) {
      nodes.push(
        <div key={`md-${lastIndex}`} className={styles.markdown}>
          <ReactMarkdown>{before}</ReactMarkdown>
        </div>
      );
    }

    const entry = citationMap[key];
    if (entry) {
      const isDoc = isDocumentCitation(entry);
      const isWeb = entry.type === 'web' && entry.url;

      if (isDoc && onDocCitationClick) {
        nodes.push(
          <span
            key={`cite-${match.index}`}
            className={`${styles.citationChip} ${styles.citationDoc}`}
            title={citationLabel(entry)}
            onClick={() => onDocCitationClick(key, entry)}
            role="button"
            tabIndex={0}
          >
            <HiOutlineDocumentText size={11} />
            {key}
          </span>,
        );
      } else if (isWeb) {
        nodes.push(
          <a
            key={`cite-${match.index}`}
            href={entry.url}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.citationChip}
            title={citationLabel(entry)}
          >
            <HiOutlineGlobeAlt size={11} />
            {key}
          </a>,
        );
      } else {
        nodes.push(
          <span
            key={`cite-${match.index}`}
            className={`${styles.citationChip} ${isDoc ? styles.citationDoc : ''}`}
            title={citationLabel(entry)}
          >
            {key}
          </span>,
        );
      }
    } else {
      nodes.push(
        <span key={`cite-${match.index}`} className={styles.citationChip} title={key}>
          {key}
        </span>,
      );
    }

    lastIndex = match.index + match[0].length;
  }

  const remaining = text.slice(lastIndex);
  if (remaining) {
    nodes.push(
      <div key={`md-${lastIndex}`} className={styles.markdown}>
        <ReactMarkdown>{remaining}</ReactMarkdown>
      </div>
    );
  }

  return nodes;
}

const ChatBubble: FC<ChatBubbleProps> = ({ message }) => {
  const [showSources, setShowSources] = useState(false);
  const [pdfModal, setPdfModal] = useState<{ key: string; entry: CitationEntry } | null>(null);
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const citationMap: CitationMap = message.citation_map ?? {};
  const hasSources =
    message.sources &&
    (Array.isArray(message.sources) ? message.sources.length > 0 : true);
  const hasCitations = Object.keys(citationMap).length > 0;

  const handleDocCitationClick = useCallback(
    (key: string, entry: CitationEntry) => {
      setPdfModal({ key, entry });
    },
    [],
  );

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  return (
    <div className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.avatar}>
        {isUser ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a4 4 0 0 1 4 4v2h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2V6a4 4 0 0 1 4-4z" />
            <circle cx="9" cy="14" r="1" />
            <circle cx="15" cy="14" r="1" />
          </svg>
        )}
      </div>

      <div className={styles.body}>
        <div className={styles.bubble}>
          {isUser ? (
            <div className={styles.userText}>
              {message.content.split('\n').map((line, i) => (
                <span key={i}>
                  {line}
                  {i < message.content.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
          ) : (
            <div className={styles.assistantContent}>
              {hasCitations
                ? renderContentWithCitations(message.content, citationMap, handleDocCitationClick)
                : <div className={styles.markdown}><ReactMarkdown>{message.content}</ReactMarkdown></div>
              }
            </div>
          )}
        </div>

        {!isUser && message.graph && (
          <ChartRenderer graph={message.graph} />
        )}

        {!isUser && message.diagnosis && (
          <DiagnosisCard diagnosis={message.diagnosis} />
        )}

        {/* Meta info bar */}
        <div className={styles.meta}>
          {!isUser && message.route && (
            <span className={`${styles.badge} ${styles[`badge_${message.route}`] ?? ''}`}>
              {message.route}
            </span>
          )}
          {!isUser && message.agent_used && (
            <span className={styles.metaItem}>
              <HiOutlineCpuChip size={12} />
              {message.agent_used}
            </span>
          )}
          {!isUser && message.processing_time !== null && (
            <span className={styles.metaItem}>
              <HiOutlineClock size={12} />
              {message.processing_time}s
            </span>
          )}
          <span className={styles.timestamp}>
            {formatTime(message.created_at)}
          </span>

          {!isUser && (
            <button
              className={styles.copyBtn}
              onClick={handleCopy}
              title={copied ? 'Copied!' : 'Copy response'}
            >
              {copied ? <HiOutlineCheck size={13} /> : <HiOutlineClipboard size={13} />}
            </button>
          )}

          {!isUser && (
            <FeedbackButtons messageId={message.id} currentFeedback={message.feedback} />
          )}
        </div>

        {/* Sources panel */}
        {!isUser && (hasCitations || hasSources) && (
          <>
            <button
              className={styles.sourcesToggle}
              onClick={() => setShowSources((p) => !p)}
            >
              <HiOutlineDocumentText size={14} />
              {showSources ? 'Hide' : 'View'} Sources
              {showSources ? <HiOutlineChevronUp size={14} /> : <HiOutlineChevronDown size={14} />}
            </button>

            {showSources && (
              <div className={styles.sourcesList}>
                {hasCitations && (
                  <>
                    <div className={styles.sourceGroup}>References</div>
                    {Object.entries(citationMap).map(([key, entry]) => (
                      <div key={key} className={styles.sourceItem}>
                        <span className={`${styles.citationChipSmall} ${entry.type === 'web' ? '' : styles.citationDoc}`}>
                          {entry.type === 'web' ? <HiOutlineGlobeAlt size={10} /> : <HiOutlineDocumentText size={10} />}
                          {key}
                        </span>
                        {entry.type === 'web' && entry.url ? (
                          <a href={entry.url} target="_blank" rel="noopener noreferrer">
                            {entry.title ?? entry.url}
                          </a>
                        ) : isDocumentCitation(entry) ? (
                          <span
                            className={styles.docLink}
                            onClick={() => handleDocCitationClick(key, entry)}
                            role="button"
                            tabIndex={0}
                          >
                            {entry.source ?? 'Unknown document'}
                          </span>
                        ) : (
                          <span>{entry.source ?? entry.title ?? 'Unknown document'}</span>
                        )}
                        {entry.score !== undefined && (
                          <span className={styles.scoreTag}>
                            {(entry.score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    ))}
                  </>
                )}

                {!hasCitations && Array.isArray(message.sources) && (
                  message.sources.map((s, i) => (
                    <div key={i} className={styles.sourceItem}>
                      <HiOutlineDocumentText size={12} className={styles.sourceIcon} />
                      {s.source ?? s.title ?? s.url ?? 'Unknown source'}
                      {s.score !== undefined && (
                        <span className={styles.scoreTag}>{(s.score * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  ))
                )}

                {!hasCitations && isHybridSources(message.sources) && (
                  <>
                    {message.sources.internal?.length > 0 && (
                      <>
                        <div className={styles.sourceGroup}>Internal Documents</div>
                        {message.sources.internal.map((s, i) => (
                          <div key={`int-${i}`} className={styles.sourceItem}>
                            <HiOutlineDocumentText size={12} className={styles.sourceIcon} />
                            {s.source ?? 'Unknown'}
                          </div>
                        ))}
                      </>
                    )}
                    {message.sources.external?.length > 0 && (
                      <>
                        <div className={styles.sourceGroup}>External Sources</div>
                        {message.sources.external.map((s, i) => (
                          <div key={`ext-${i}`} className={styles.sourceItem}>
                            <HiOutlineGlobeAlt size={12} className={styles.sourceIcon} />
                            {s.url ? (
                              <a href={s.url} target="_blank" rel="noopener noreferrer">
                                {s.title ?? s.url}
                              </a>
                            ) : (
                              s.title ?? 'Unknown'
                            )}
                          </div>
                        ))}
                      </>
                    )}
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {pdfModal && (
        <PdfViewerModal
          entry={pdfModal.entry}
          citationKey={pdfModal.key}
          onClose={() => setPdfModal(null)}
        />
      )}
    </div>
  );
};

export default ChatBubble;
