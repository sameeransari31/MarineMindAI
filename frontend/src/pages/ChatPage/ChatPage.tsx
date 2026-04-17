import { type FC, useRef, useEffect, useCallback, useState } from 'react';
import { ChatBubble, ChatInput, TypingIndicator, WelcomeScreen } from '@/components';
import { useChat } from '@/hooks';
import type { ChatSession } from '@/types';
import { HiOutlineCog6Tooth, HiOutlineChevronDown, HiOutlineExclamationTriangle } from 'react-icons/hi2';
import toast, { Toaster } from 'react-hot-toast';
import styles from './ChatPage.module.css';

interface ChatPageProps {
  sessions: ChatSession[];
  currentSessionId: string | null;
  onSessionsChange: () => void;
  onSessionCreated: (id: string) => void;
}

const ChatPage: FC<ChatPageProps> = ({ onSessionsChange, currentSessionId, onSessionCreated }) => {
  const { messages, isLoading, error, send, startNewChat, loadSession, sessionId } = useChat();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const chatAreaRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  useEffect(() => {
    if (currentSessionId && currentSessionId !== sessionId) {
      loadSession(currentSessionId);
    } else if (currentSessionId === null && sessionId !== null) {
      startNewChat();
    }
  }, [currentSessionId, sessionId, loadSession, startNewChat]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleScroll = useCallback(() => {
    const el = chatAreaRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(distanceFromBottom > 200);
  }, []);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = useCallback(
    async (message: string) => {
      const res = await send(message);
      if (res) {
        onSessionCreated(res.session_id);
        onSessionsChange();
      } else {
        toast.error('Failed to get a response. Please try again.', {
          style: {
            background: 'var(--bg-card)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-primary)',
            fontSize: '13px',
          },
        });
      }
    },
    [send, onSessionsChange, onSessionCreated]
  );

  const chatTitle = sessionId
    ? (messages[0]?.content.slice(0, 50) ?? 'Chat')
    : 'New Conversation';

  return (
    <div className={styles.page}>
      <Toaster position="top-right" />
      <div className={styles.topbar}>
        <div className={styles.topbarLeft}>
          <div className={styles.topbarDot} />
          <h1 className={styles.title}>{chatTitle}</h1>
        </div>
        <a
          href="/admin/"
          target="_blank"
          rel="noopener noreferrer"
          className={styles.adminLink}
          title="Admin Panel"
        >
          <HiOutlineCog6Tooth size={16} />
          <span className={styles.adminText}>Admin</span>
        </a>
      </div>

      <div className={styles.chatArea} ref={chatAreaRef} onScroll={handleScroll}>
        <div className={styles.chatInner}>
          {error && (
            <div className={styles.errorBanner}>
              <HiOutlineExclamationTriangle size={16} />
              <span>{error}</span>
            </div>
          )}
          {messages.length === 0 && !isLoading ? (
            <WelcomeScreen onSuggestion={handleSend} />
          ) : (
            messages.map((msg) => <ChatBubble key={msg.id} message={msg} />)
          )}
          {isLoading && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>
      </div>

      {showScrollBtn && (
        <button className={styles.scrollBtn} onClick={scrollToBottom} aria-label="Scroll to bottom">
          <HiOutlineChevronDown size={18} />
        </button>
      )}

      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
};

export default ChatPage;
