import { type FC, useEffect, useRef } from 'react';
import type { AlertEntry } from '@/types';
import styles from './AlertToast.module.css';

interface AlertToastProps {
  alerts: AlertEntry[];
  onDismiss: (id: string) => void;
}

const SEVERITY_ICON: Record<string, string> = {
  critical: '!!',
  error: '!',
  warning: '⚠',
  info: 'i',
};

const ICON_CLASS: Record<string, string> = {
  critical: `${styles.icon} ${styles.iconCritical}`,
  error: `${styles.icon} ${styles.iconError}`,
  warning: `${styles.icon} ${styles.iconWarning}`,
  info: `${styles.icon} ${styles.iconInfo}`,
};

const SEV_CLASS: Record<string, string> = {
  critical: styles.sevCritical,
  error: styles.sevError,
  warning: styles.sevWarning,
  info: styles.sevInfo,
};

const AUTO_DISMISS_MS = 8000;

const AlertToast: FC<AlertToastProps> = ({ alerts, onDismiss }) => {
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    alerts.forEach((alert) => {
      if (!timers.current.has(alert.id)) {
        const timer = setTimeout(() => {
          onDismiss(alert.id);
          timers.current.delete(alert.id);
        }, AUTO_DISMISS_MS);
        timers.current.set(alert.id, timer);
      }
    });

    return () => {
      timers.current.forEach((t) => clearTimeout(t));
      timers.current.clear();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alerts.length]);

  if (alerts.length === 0) return null;

  return (
    <div className={styles.toastContainer}>
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={styles.toast}
          onClick={() => onDismiss(alert.id)}
          role="alert"
        >
          <div className={ICON_CLASS[alert.severity] || styles.iconInfo}>
            {SEVERITY_ICON[alert.severity] || 'i'}
          </div>
          <div className={styles.body}>
            <div className={`${styles.severity} ${SEV_CLASS[alert.severity] || ''}`}>
              {alert.severity} &middot; {alert.alert_type}
            </div>
            <div className={styles.title}>{alert.title}</div>
            <div className={styles.message}>{alert.message}</div>
          </div>
          <button
            className={styles.close}
            onClick={(e) => {
              e.stopPropagation();
              onDismiss(alert.id);
            }}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      ))}
    </div>
  );
};

export default AlertToast;
