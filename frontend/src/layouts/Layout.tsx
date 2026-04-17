import { type FC, useState, useCallback, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar, AlertToast } from '@/components';
import { fetchSessions } from '@/api';
import { useAlertPolling } from '@/hooks';
import type { AuthUser } from '@/api';
import type { ChatSession } from '@/types';
import { HiOutlineBars3 } from 'react-icons/hi2';
import styles from './Layout.module.css';

interface LayoutProps {
  onSessionSelect: (id: string) => void;
  onNewChat: () => void;
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSessionsRefresh?: () => void;
  user: AuthUser;
  onLogout: () => void;
}

const Layout: FC<LayoutProps> = ({
  onSessionSelect,
  onNewChat,
  sessions,
  currentSessionId,
  user,
  onLogout,
}) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { newAlerts, dismissAlert } = useAlertPolling();

  const handleSessionSelect = (id: string) => {
    onSessionSelect(id);
    setSidebarOpen(false);
  };

  const handleNewChat = () => {
    onNewChat();
    setSidebarOpen(false);
  };

  return (
    <div className={styles.layout}>
      <button
        className={styles.hamburger}
        onClick={() => setSidebarOpen(true)}
        aria-label="Open menu"
      >
        <HiOutlineBars3 />
      </button>

      {sidebarOpen && (
        <div className={styles.overlay} onClick={() => setSidebarOpen(false)} />
      )}

      <Sidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onNewChat={handleNewChat}
        onSelectSession={handleSessionSelect}
        username={user.username}
        onLogout={onLogout}
        mobileOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className={styles.main}>
        <Outlet />
      </main>

      <AlertToast alerts={newAlerts} onDismiss={dismissAlert} />
    </div>
  );
};

export default Layout;

// Hook to manage layout-level state
export function useLayoutState() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await fetchSessions();
      setSessions(data);
    } catch {
      // Silently fail — sidebar just won't update
    }
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  return {
    sessions,
    currentSessionId,
    setCurrentSessionId,
    refreshSessions,
  };
}
