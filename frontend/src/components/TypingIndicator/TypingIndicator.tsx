import { type FC, useState, useEffect } from 'react';
import styles from './TypingIndicator.module.css';

const statusMessages = [
  'Analyzing your query...',
  'Searching documents...',
  'Generating response...',
];

const TypingIndicator: FC = () => {
  const [msgIndex, setMsgIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setMsgIndex((i) => (i + 1) % statusMessages.length);
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className={styles.wrapper}>
      <div className={styles.avatar}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a4 4 0 0 1 4 4v2h2a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2V6a4 4 0 0 1 4-4z" />
          <circle cx="9" cy="14" r="1" />
          <circle cx="15" cy="14" r="1" />
        </svg>
      </div>
      <div className={styles.bubble}>
        <div className={styles.dots}>
          <span className={styles.dot} />
          <span className={styles.dot} />
          <span className={styles.dot} />
        </div>
        <span className={styles.label} key={msgIndex}>{statusMessages[msgIndex]}</span>
      </div>
    </div>
  );
};

export default TypingIndicator;
