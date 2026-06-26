/**
 * ChatWindow — Main chat interface with session loading, confidence badges,
 * sources, bridge responses, and copy-to-clipboard.
 */

import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { chatAPI, chatExportAPI } from '../../api/client';
import ReactMarkdown from 'react-markdown';
import {
  Send, Zap, MessageSquare, ThumbsUp, ThumbsDown,
  FileText, ChevronDown, ChevronUp, AlertTriangle, Sparkles,
  Copy, Check, Download,
} from 'lucide-react';
import './ChatWindow.css';

const SUGGESTED_QUESTIONS = [
  "How does authentication work?",
  "Can we integrate with Salesforce?",
  "What's the pricing for enterprise?",
  "Is the platform GDPR compliant?",
  "What's your quantum computing roadmap?",
  "How does auto-scaling work?",
];

export default function ChatWindow({ activeSessionId, onSessionCreated }) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load session when activeSessionId changes
  useEffect(() => {
    if (activeSessionId === null) {
      // New chat
      setMessages([]);
      setSessionId(null);
    } else if (activeSessionId !== sessionId) {
      loadSession(activeSessionId);
    }
  }, [activeSessionId]);

  const loadSession = async (sid) => {
    try {
      const res = await chatAPI.getSessionMessages(sid);
      const loaded = res.data.map((m) => ([
        { type: 'user', text: m.question },
        {
          type: 'ai',
          id: m.id,
          text: m.answer,
          confidence: m.confidence,
          sources: m.sources || [],
          isBridge: m.is_bridge_response,
          rating: m.rating || 0,
        },
      ])).flat();
      setMessages(loaded);
      setSessionId(sid);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const sendMessage = async (question) => {
    if (!question.trim() || isLoading) return;

    const userMsg = { type: 'user', text: question };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ question, session_id: sessionId }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to connect to stream');
      }

      // Insert placeholder AI message
      const initialAiMsg = {
        type: 'ai',
        text: '',
        confidence: null,
        sources: [],
        bridgeResponse: null,
        isBridge: false,
        rating: 0,
        responseTime: null,
        isStreaming: true,
      };
      setMessages(prev => [...prev, initialAiMsg]);

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let done = false;
      let buffer = '';
      let fullText = '';
      let metadata = null;

      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          buffer += decoder.decode(value, { stream: !done });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || !trimmed.startsWith('data: ')) continue;

            try {
              const parsed = JSON.parse(trimmed.slice(6));
              if (parsed.type === 'token') {
                fullText += parsed.content;
                setMessages(prev => {
                  const updated = [...prev];
                  const lastIndex = updated.length - 1;
                  if (updated[lastIndex] && updated[lastIndex].type === 'ai') {
                    updated[lastIndex] = {
                      ...updated[lastIndex],
                      text: fullText,
                    };
                  }
                  return updated;
                });
              } else if (parsed.type === 'done') {
                metadata = parsed;
              }
            } catch (e) {
              console.error('Error parsing SSE line:', e, trimmed);
            }
          }
        }
      }

      if (metadata) {
        if (!sessionId && metadata.session_id) {
          setSessionId(metadata.session_id);
          if (onSessionCreated) onSessionCreated(metadata.session_id);
        }

        setMessages(prev => {
          const updated = [...prev];
          const lastIndex = updated.length - 1;
          if (updated[lastIndex] && updated[lastIndex].type === 'ai') {
            updated[lastIndex] = {
              ...updated[lastIndex],
              id: metadata.id,
              text: metadata.is_bridge_response ? metadata.bridge_response : fullText,
              confidence: metadata.confidence,
              sources: metadata.sources || [],
              bridgeResponse: metadata.bridge_response,
              isBridge: metadata.is_bridge_response,
              responseTime: metadata.response_time_ms,
              isStreaming: false,
            };
          }
          return updated;
        });

        // Refresh sidebar history
        if (window.__refreshSidebarHistory) window.__refreshSidebarHistory();
      }

    } catch (err) {
      console.error('Error in streaming chat:', err);
      const errorMsg = {
        type: 'ai',
        text: err.message || 'Something went wrong. Please try again.',
        confidence: { tier: 'LOW', score: 0 },
        sources: [],
        isError: true,
      };
      setMessages(prev => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (updated[lastIndex] && updated[lastIndex].type === 'ai' && updated[lastIndex].isStreaming) {
          updated[lastIndex] = errorMsg;
          return updated;
        }
        return [...prev, errorMsg];
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleRate = async (msgIndex, rating) => {
    const msg = messages[msgIndex];
    if (!msg.id) return;

    try {
      await chatAPI.rateResponse(msg.id, rating);
      setMessages(prev =>
        prev.map((m, i) => i === msgIndex ? { ...m, rating } : m)
      );
    } catch (err) {
      console.error('Rating failed:', err);
    }
  };

  const getInitials = (name) => {
    return name?.split(' ').map(n => n[0]).join('').toUpperCase() || '?';
  };

  const handleExportPDF = async () => {
    if (!sessionId) return;
    try {
      const res = await chatExportAPI.exportSessionPDF(sessionId);
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = `chat_export_${sessionId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('PDF export failed:', err);
    }
  };

  return (
    <div className="chat-page">
      {/* Header */}
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-icon">
            <Sparkles size={18} color="white" />
          </div>
          <div className="chat-header-info">
            <h2>Knowledge Assistant</h2>
            <div className="chat-header-status">
              <span className="status-dot" />
              Online — Ready to help
            </div>
          </div>
        </div>
        {sessionId && messages.length > 0 && (
          <button
            className="btn btn-ghost btn-sm"
            onClick={handleExportPDF}
            title="Export as PDF"
            style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.82rem' }}
          >
            <Download size={14} /> PDF
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <MessageSquare size={36} color="white" />
            </div>
            <h3>Ask me anything about your knowledge base</h3>
            <p>
              I'll search your documents and give you client-ready answers
              with confidence levels and source citations.
            </p>
            <div className="suggested-questions">
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button
                  key={i}
                  className="suggested-q"
                  onClick={() => sendMessage(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.type}`}>
              <div className="message-avatar">
                {msg.type === 'user' ? getInitials(user?.full_name) : <Zap size={16} />}
              </div>
              <div className="message-content">
                <div className="message-bubble">
                  {msg.type === 'ai' ? (
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  ) : (
                    msg.text
                  )}
                </div>

                {msg.type === 'ai' && msg.confidence && (
                  <>
                    {/* Confidence Badge */}
                    <div className="confidence-section">
                      <span className={`confidence-badge ${msg.confidence.tier.toLowerCase()}`}>
                        {msg.confidence.tier === 'HIGH' && '✓ '}
                        {msg.confidence.tier === 'MEDIUM' && '~ '}
                        {msg.confidence.tier === 'LOW' && '! '}
                        {msg.confidence.tier} Confidence
                      </span>
                      <span className="confidence-score">
                        Score: {(msg.confidence.score * 100).toFixed(0)}%
                      </span>
                      {msg.responseTime && (
                        <span className="response-time">
                          {(msg.responseTime / 1000).toFixed(1)}s
                        </span>
                      )}
                    </div>

                    {/* Bridge Response */}
                    {msg.bridgeResponse && msg.confidence.tier === 'MEDIUM' && (
                      <div className="bridge-response">
                        <div className="bridge-label">
                          <AlertTriangle size={12} />
                          Suggested Follow-Up Script
                        </div>
                        <div className="bridge-text">{msg.bridgeResponse}</div>
                      </div>
                    )}

                    {msg.isBridge && msg.confidence.tier === 'LOW' && (
                      <div className="bridge-response" style={{
                        borderColor: 'rgba(239, 68, 68, 0.2)',
                        background: 'rgba(239, 68, 68, 0.06)',
                        borderLeftColor: 'var(--confidence-low)'
                      }}>
                        <div className="bridge-label" style={{ color: 'var(--confidence-low)' }}>
                          <AlertTriangle size={12} />
                          Bridge Response — Use This in Meeting
                        </div>
                        <div className="bridge-text">
                          This response is designed to keep the conversation professional while
                          committing to a follow-up.
                        </div>
                      </div>
                    )}

                    {/* Sources */}
                    {msg.sources && msg.sources.length > 0 && (
                      <SourcesViewer sources={msg.sources} />
                    )}

                    {/* Feedback + Copy */}
                    {!msg.isError && (
                      <div className="message-feedback">
                        <CopyButton text={msg.text} />
                        <button
                          className={`feedback-btn ${msg.rating === 1 ? 'active-up' : ''}`}
                          onClick={() => handleRate(idx, 1)}
                        >
                          <ThumbsUp size={13} /> Helpful
                        </button>
                        <button
                          className={`feedback-btn ${msg.rating === -1 ? 'active-down' : ''}`}
                          onClick={() => handleRate(idx, -1)}
                        >
                          <ThumbsDown size={13} />
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))
        )}

        {/* Typing Indicator */}
        {isLoading && (
          <div className="typing-indicator">
            <div className="message-avatar" style={{
              background: 'rgba(6, 182, 212, 0.15)',
              border: '1px solid rgba(6, 182, 212, 0.3)',
              color: 'var(--accent-cyan)',
              width: 36, height: 36, borderRadius: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={16} />
            </div>
            <div className="typing-dots">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <form className="chat-input-wrapper" onSubmit={handleSubmit}>
          <textarea
            ref={inputRef}
            className="chat-input"
            placeholder="Ask a client question... e.g. 'How does authentication work?'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || isLoading}
          >
            <Send size={18} />
          </button>
        </form>
        <div className="chat-input-hint">
          Answers are grounded in your knowledge base documents. Press Enter to send.
        </div>
      </div>
    </div>
  );
}


/* ── Copy Button Sub-Component ────────────────────────────── */
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  };

  return (
    <button
      className={`feedback-btn ${copied ? 'active-up' : ''}`}
      onClick={handleCopy}
      title="Copy to clipboard"
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? 'Copied!' : 'Copy'}
    </button>
  );
}


/* ── Sources Viewer Sub-Component ─────────────────────────── */
function SourcesViewer({ sources }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="sources-section">
      <button className="sources-toggle" onClick={() => setExpanded(!expanded)}>
        <FileText size={12} />
        {sources.length} source{sources.length !== 1 ? 's' : ''}
        {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
      </button>
      {expanded && (
        <div className="sources-list">
          {sources.map((source, i) => (
            <div key={i} className="source-item">
              <FileText size={14} style={{ color: 'var(--accent-blue)', flexShrink: 0 }} />
              <span className="source-name">{source.filename}</span>
              <span className="source-preview">{source.preview}</span>
              <span className="source-score">{(source.score * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
