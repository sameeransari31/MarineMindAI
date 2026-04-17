import { type FC, useState } from 'react';
import { submitMessageFeedback } from '@/api';
import {
  HiOutlineHandThumbUp,
  HiOutlineHandThumbDown,
  HiHandThumbUp,
  HiHandThumbDown,
} from 'react-icons/hi2';
import styles from './FeedbackButtons.module.css';

interface FeedbackButtonsProps {
  messageId: string;
  currentFeedback?: string;
}

const FeedbackButtons: FC<FeedbackButtonsProps> = ({ messageId, currentFeedback }) => {
  const [feedback, setFeedback] = useState<string | undefined>(currentFeedback);
  const [showNote, setShowNote] = useState(false);
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleFeedback = async (value: 'correct' | 'incorrect') => {
    if (submitting) return;

    // If already selected, toggle off not supported by API — just ignore
    if (feedback === value) return;

    setSubmitting(true);
    try {
      await submitMessageFeedback(messageId, value);
      setFeedback(value);
      if (value === 'incorrect') {
        setShowNote(true);
      } else {
        setShowNote(false);
      }
    } catch {
      // silently fail — don't break chat UX
    } finally {
      setSubmitting(false);
    }
  };

  const handleNoteSubmit = async () => {
    if (!note.trim() || submitting) return;
    setSubmitting(true);
    try {
      await submitMessageFeedback(messageId, 'incorrect', note.trim());
      setShowNote(false);
    } catch {
      // silently fail
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.wrapper}>
      <div className={styles.buttons}>
        <button
          className={`${styles.feedbackBtn} ${feedback === 'correct' ? styles.active : ''}`}
          onClick={() => handleFeedback('correct')}
          disabled={submitting}
          title="Helpful"
        >
          {feedback === 'correct' ? <HiHandThumbUp size={16} /> : <HiOutlineHandThumbUp size={16} />}
        </button>
        <button
          className={`${styles.feedbackBtn} ${feedback === 'incorrect' ? styles.activeNeg : ''}`}
          onClick={() => handleFeedback('incorrect')}
          disabled={submitting}
          title="Not helpful"
        >
          {feedback === 'incorrect' ? <HiHandThumbDown size={16} /> : <HiOutlineHandThumbDown size={16} />}
        </button>
      </div>

      {showNote && (
        <div className={styles.noteBox}>
          <textarea
            className={styles.noteInput}
            placeholder="What was wrong? (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={2000}
            rows={2}
          />
          <div className={styles.noteActions}>
            <button
              className={styles.noteCancel}
              onClick={() => setShowNote(false)}
            >
              Skip
            </button>
            <button
              className={styles.noteSubmit}
              onClick={handleNoteSubmit}
              disabled={!note.trim() || submitting}
            >
              Submit
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FeedbackButtons;
