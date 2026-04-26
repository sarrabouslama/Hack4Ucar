import React, { useEffect, useRef, useState } from 'react';
import { getChatSession, listChatSessions, sendChatMessage } from '../api/chatbotApi';

const DOMAIN_COLORS: Record<string, string> = {
  education: '#3b82f6',
  finance: '#10b981',
  environment: '#f59e0b',
  '': '#c9a84c',
};

const DOMAIN_LABELS: Record<string, string> = {
  education: 'Education',
  finance: 'Finance',
  environment: 'Environment',
  '': 'General',
};

const USER_ID = 'ucar-central';

interface MessageView {
  role: 'user' | 'bot';
  content: string;
  time: string;
}

interface SessionSummary {
  session_id: string;
  session_name?: string | null;
  domain_context?: string | null;
  message_count: number;
  last_message_at?: string | null;
}

interface SessionHistoryItem {
  user_message: string;
  bot_response: string;
  message_timestamp: string;
  domain_context?: string | null;
}

interface SessionDetail {
  session_id: string;
  domain_context?: string | null;
  history: SessionHistoryItem[];
}

interface ChatResponsePayload {
  session_id: string;
  answer: string;
}

const formatTime = (value?: string) => {
  if (!value) {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
};

const Chatbot: React.FC = () => {
  const [input, setInput] = useState('');
  const [domain, setDomain] = useState('');
  const [messages, setMessages] = useState<MessageView[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadSessions = async () => {
    try {
      const res = await listChatSessions(USER_ID);
      setSessions(res.data);
    } catch (err) {
      console.error('Failed to load sessions', err);
    }
  };

  const loadSessionChat = async (id: string) => {
    try {
      const res = await getChatSession(id);
      const data = res.data as SessionDetail;

      setActiveSessionId(data.session_id);
      setDomain(data.domain_context || '');
      setMessages(
        (data.history || []).flatMap((item) => [
          {
            role: 'user' as const,
            content: item.user_message,
            time: formatTime(item.message_timestamp),
          },
          {
            role: 'bot' as const,
            content: item.bot_response,
            time: formatTime(item.message_timestamp),
          },
        ]),
      );
    } catch (err) {
      console.error('Failed to load chat', err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = async (overrideInput?: string) => {
    const textToSend = overrideInput || input;
    if (!textToSend.trim()) {
      return;
    }

    const timestamp = formatTime();
    const userMessage: MessageView = {
      role: 'user',
      content: textToSend,
      time: timestamp,
    };

    setMessages((prev) => [...prev, userMessage]);
    if (!overrideInput) {
      setInput('');
    }
    setIsTyping(true);

    try {
      const payload = {
        session_id: activeSessionId,
        user_id: USER_ID,
        message: textToSend,
        domain_context: domain || undefined,
      };

      const res = await sendChatMessage(payload);
      const data = res.data as ChatResponsePayload;

      if (!activeSessionId && data.session_id) {
        setActiveSessionId(data.session_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          content: data.answer,
          time: formatTime(),
        },
      ]);

      await loadSessions();
    } catch (err) {
      console.error('Chat failed', err);
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          content: 'Sorry, I encountered an error communicating with the server.',
          time: formatTime(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const startNewSession = () => {
    setActiveSessionId(null);
    setMessages([]);
    setDomain('');
    setInput('');
  };

  return (
    <div className="main module-panel">
      <div className="chat-header">
        <div className="header-left">
          <div className="header-title">UniBot Assistant</div>
          <div className="header-status">
            <span className="status-dot"></span>
            Online · Institutional assistant
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div className="domain-pill">{DOMAIN_LABELS[domain]}</div>
          <button className="new-btn new-btn--inline" onClick={startNewSession}>
            New conversation
          </button>
        </div>
      </div>

      <div className="module-toolbar">
        <div className="module-toolbar-title">Recent conversations</div>
        <div className="session-strip">
          {sessions.length === 0 ? (
            <div className="session-empty-inline">No conversations yet</div>
          ) : (
            sessions.map((session) => (
              <button
                key={session.session_id}
                className={`session-chip ${activeSessionId === session.session_id ? 'active' : ''}`}
                onClick={() => loadSessionChat(session.session_id)}
              >
                <span className="session-chip-name">{session.session_name || 'Untitled session'}</span>
                <span className="session-chip-meta">{session.message_count} msg</span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-icon">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={DOMAIN_COLORS[domain]} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <div className="welcome-title">Good day, UCAR Central</div>
            <div className="welcome-desc">
              I&apos;m UniBot, your institutional intelligence assistant. Ask me about KPIs, institutions, alerts, or reports.
            </div>
            <div className="quick-grid">
              <button className="quick-card" onClick={() => handleSend('Which institutions are performing best this quarter?')}>
                <span className="quick-card-icon">01</span>
                Quarterly performance
              </button>
              <button className="quick-card" onClick={() => handleSend('Show me the latest alerts and anomalies across all domains.')}>
                <span className="quick-card-icon">02</span>
                Latest alerts
              </button>
            </div>
          </div>
        ) : (
          messages.map((message, idx) => (
            <div key={`${message.role}-${idx}`} className={`msg-row ${message.role === 'user' ? 'user' : ''}`}>
              <div className={`msg-avatar ${message.role === 'user' ? 'user' : 'bot'}`}>{message.role === 'user' ? 'UC' : 'UB'}</div>
              <div className="msg-body">
                <div className={`bubble ${message.role === 'user' ? 'user' : 'bot'}`} style={{ whiteSpace: 'pre-wrap' }}>
                  {message.content}
                </div>
                <div className="bubble-time">{message.time}</div>
              </div>
            </div>
          ))
        )}

        {isTyping && (
          <div className="typing-row">
            <div className="msg-avatar bot">UB</div>
            <div className="typing-bubble">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <div className="input-box">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            id="user-input"
            placeholder="Ask about KPIs, institutions, alerts, or reports..."
            rows={1}
          />
          <button className="doc-btn" title="Upload document" type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="17 8 12 3 7 8" />
              <line x1="12" y1="3" x2="12" y2="15" />
            </svg>
          </button>
          <button className="send-btn" onClick={() => handleSend()} disabled={!input.trim()} type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>

        <div className="input-footer">
          <div className="domain-chips">
            <button className={`d-chip ${domain === '' ? 'active' : ''}`} onClick={() => setDomain('')} type="button">
              General
            </button>
            <button className={`d-chip ${domain === 'education' ? 'active' : ''}`} onClick={() => setDomain('education')} type="button">
              Education
            </button>
            <button className={`d-chip ${domain === 'finance' ? 'active' : ''}`} onClick={() => setDomain('finance')} type="button">
              Finance
            </button>
            <button className={`d-chip ${domain === 'environment' ? 'active' : ''}`} onClick={() => setDomain('environment')} type="button">
              Environment
            </button>
          </div>
          <span className="input-hint">Enter to send · Shift+Enter for newline</span>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;
