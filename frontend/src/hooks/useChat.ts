import { useState, useCallback } from 'react';
import type { ChatMessage, ChatResponse } from '@/types';
import { sendMessage, fetchSessionMessages } from '@/api';

interface UseChatReturn {
  messages: ChatMessage[];
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  send: (message: string) => Promise<ChatResponse | null>;
  loadSession: (id: string) => Promise<void>;
  startNewChat: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (message: string): Promise<ChatResponse | null> => {
      setIsLoading(true);
      setError(null);

      // Optimistically add user message
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: message,
        agent_used: '',
        route: '',
        sources: [],
        citation_map: {},
        processing_time: null,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const res = await sendMessage(message, sessionId ?? undefined);
        setSessionId(res.session_id);

        const assistantMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: res.answer,
          agent_used: res.agent,
          route: res.route,
          sources: res.sources,
          citation_map: res.citation_map ?? {},
          processing_time: res.processing_time,
          created_at: new Date().toISOString(),
          graph: res.graph ?? null,
          graph_intent: res.graph_intent ?? null,
          diagnosis: res.diagnosis ?? null,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        return res;
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Something went wrong';
        setError(errMsg);

        const errorMsg: ChatMessage = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Connection error. Please check the server and try again.',
          agent_used: 'system',
          route: 'error',
          sources: [],
          citation_map: {},
          processing_time: null,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  const loadSession = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const msgs = await fetchSessionMessages(id);
      setMessages(msgs);
      setSessionId(id);
    } catch {
      setError('Failed to load session');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const startNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setError(null);
  }, []);

  return { messages, sessionId, isLoading, error, send, loadSession, startNewChat };
}
