import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout, useLayoutState } from '@/layouts';
import { ChatPage, DashboardPage, DocumentsPage, LoginPage, VesselsPage, NoonReportsPage } from '@/pages';
import { useAuth } from '@/hooks';

function App() {
  const { user, isLoading, error, login, logout } = useAuth();
  const { sessions, currentSessionId, setCurrentSessionId, refreshSessions } =
    useLayoutState();

  const handleNewChat = () => {
    setCurrentSessionId(null);
  };

  const handleSessionSelect = (id: string) => {
    setCurrentSessionId(id);
  };

  // Show branded loading screen while checking session
  if (isLoading) {
    return (
      <div
        style={{
          height: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-primary)',
          color: 'var(--text-primary)',
          gap: '20px',
        }}
      >
        <div
          style={{
            width: 64,
            height: 64,
            borderRadius: 16,
            background: 'linear-gradient(135deg, var(--accent), #0088a8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            boxShadow: '0 4px 24px rgba(0, 180, 216, 0.3)',
            animation: 'pulse 2s infinite',
          }}
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-1H2v1z"/>
            <path d="M12 2L12 17"/>
            <path d="M8 6l4-4 4 4"/>
            <path d="M4 19c2-3 4-5 8-5s6 2 8 5"/>
          </svg>
        </div>
        <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700, letterSpacing: '-0.3px' }}>
          MarineMind
        </div>
        <div
          style={{
            width: 160,
            height: 3,
            background: 'var(--bg-card)',
            borderRadius: 4,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: '40%',
              height: '100%',
              background: 'var(--accent)',
              borderRadius: 4,
              animation: 'shimmer 1.2s infinite',
              backgroundSize: '200% 100%',
              backgroundImage: 'linear-gradient(90deg, var(--accent) 0%, var(--accent-hover) 50%, var(--accent) 100%)',
            }}
          />
        </div>
      </div>
    );
  }

  // Show login page if not authenticated
  if (!user) {
    return <LoginPage onLogin={login} error={error} />;
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <Layout
              sessions={sessions}
              currentSessionId={currentSessionId}
              onNewChat={handleNewChat}
              onSessionSelect={handleSessionSelect}
              onSessionsRefresh={refreshSessions}
              user={user}
              onLogout={logout}
            />
          }
        >
          <Route
            index
            element={
              <ChatPage
                sessions={sessions}
                currentSessionId={currentSessionId}
                onSessionsChange={refreshSessions}
                onSessionCreated={setCurrentSessionId}
              />
            }
          />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="documents" element={<DocumentsPage />} />
          <Route path="vessels" element={<VesselsPage />} />
          <Route path="noon-reports" element={<NoonReportsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
