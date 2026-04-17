import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchAlerts } from '@/api';
import type { AlertEntry } from '@/types';

const POLL_INTERVAL = 30_000; // 30 seconds

/**
 * Hook that polls for unread alerts every 30 s and surfaces new ones as toasts.
 * Returns the latest batch of *new* (unseen) alerts so the UI can show toasts.
 */
export function useAlertPolling() {
  const [newAlerts, setNewAlerts] = useState<AlertEntry[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const seenIds = useRef<Set<string>>(new Set());
  const initialLoadDone = useRef(false);

  const poll = useCallback(async () => {
    try {
      const data = await fetchAlerts({ is_read: 'false', page_size: '10' });
      setUnreadCount(data.total);

      if (!initialLoadDone.current) {
        // First load — mark all existing as "seen" so we don't toast old alerts
        data.results.forEach((a) => seenIds.current.add(a.id));
        initialLoadDone.current = true;
        return;
      }

      const fresh = data.results.filter((a) => !seenIds.current.has(a.id));
      if (fresh.length > 0) {
        fresh.forEach((a) => seenIds.current.add(a.id));
        setNewAlerts((prev) => [...fresh, ...prev].slice(0, 5)); // keep max 5
      }
    } catch {
      // Silently fail — alerts are non-critical
    }
  }, []);

  useEffect(() => {
    void poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [poll]);

  const dismissAlert = useCallback((alertId: string) => {
    setNewAlerts((prev) => prev.filter((a) => a.id !== alertId));
  }, []);

  const dismissAll = useCallback(() => {
    setNewAlerts([]);
  }, []);

  return { newAlerts, unreadCount, dismissAlert, dismissAll };
}
