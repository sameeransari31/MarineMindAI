import { type FC } from 'react';
import { NavLink } from 'react-router-dom';
import {
  HiOutlineChatBubbleLeftRight,
  HiOutlineDocumentArrowUp,
  HiOutlinePlusCircle,
  HiArrowRightOnRectangle,
  HiOutlineXMark,
  HiOutlineChartBarSquare,
} from 'react-icons/hi2';
import { HiOutlineTruck, HiOutlineClipboardDocumentList } from 'react-icons/hi2';
import type { ChatSession } from '@/types';
import { truncate } from '@/utils';
import styles from './Sidebar.module.css';

interface SidebarProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onNewChat: () => void;
  onSelectSession: (id: string) => void;
  username?: string;
  onLogout?: () => void;
  mobileOpen?: boolean;
  onClose?: () => void;
}

const Sidebar: FC<SidebarProps> = ({
  sessions,
  currentSessionId,
  onNewChat,
  onSelectSession,
  username,
  onLogout,
  mobileOpen,
  onClose,
}) => {
  return (
    <aside className={`${styles.sidebar} ${mobileOpen ? styles.mobileOpen : ''}`}>
      <div className={styles.header}>
        <div className={styles.brand}>
          <div className={styles.logoIcon}>
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 20a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-1H2v1z"/>
              <path d="M12 2L12 17"/>
              <path d="M8 6l4-4 4 4"/>
              <path d="M4 19c2-3 4-5 8-5s6 2 8 5"/>
            </svg>
          </div>
          <div>
            <div className={styles.title}>MarineMind</div>
            <div className={styles.subtitle}>AI Maritime Assistant</div>
          </div>
        </div>
        {onClose && (
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close sidebar">
            <HiOutlineXMark size={20} />
          </button>
        )}
      </div>

      <button className={styles.newChatBtn} onClick={onNewChat}>
        <HiOutlinePlusCircle size={18} />
        New Conversation
      </button>

      <nav className={styles.nav}>
        <NavLink to="/" end className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}>
          <HiOutlineChatBubbleLeftRight size={18} />
          <span>Chat</span>
        </NavLink>
        <NavLink to="/dashboard" className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}>
          <HiOutlineChartBarSquare size={18} />
          <span>Dashboard</span>
        </NavLink>
        <NavLink to="/documents" className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}>
          <HiOutlineDocumentArrowUp size={18} />
          <span>Documents</span>
        </NavLink>
        <NavLink to="/vessels" className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}>
          <HiOutlineTruck size={18} />
          <span>Vessels</span>
        </NavLink>
        <NavLink to="/noon-reports" className={({ isActive }) => `${styles.navLink} ${isActive ? styles.active : ''}`}>
          <HiOutlineClipboardDocumentList size={18} />
          <span>Noon Reports</span>
        </NavLink>
      </nav>

      <div className={styles.sessionList}>
        <div className={styles.sessionHeader}>Recent Conversations</div>
        {(sessions ?? []).length === 0 ? (
          <div className={styles.empty}>
            <HiOutlineChatBubbleLeftRight size={24} className={styles.emptyIcon} />
            <span>No conversations yet</span>
          </div>
        ) : (
          (sessions ?? []).map((s) => (
            <button
              key={s.id}
              className={`${styles.sessionItem} ${s.id === currentSessionId ? styles.sessionActive : ''}`}
              onClick={() => onSelectSession(s.id)}
              title={s.title}
            >
              <HiOutlineChatBubbleLeftRight size={14} className={styles.sessionIcon} />
              <span className={styles.sessionTitle}>{truncate(s.title, 28)}</span>
            </button>
          ))
        )}
      </div>

      {username && (
        <div className={styles.userSection}>
          <div className={styles.userInfo}>
            <div className={styles.userAvatar}>{username.charAt(0).toUpperCase()}</div>
            <span className={styles.username}>{username}</span>
          </div>
          <button className={styles.logoutBtn} onClick={onLogout} title="Sign out">
            <HiArrowRightOnRectangle size={16} />
          </button>
        </div>
      )}
    </aside>
  );
};

export default Sidebar;
