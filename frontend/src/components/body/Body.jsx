import React, { useState, useRef, useEffect, useCallback } from "react";
import styles from "./Body.module.css";
import { FiSend, FiCopy, FiCheck, FiRefreshCw } from "react-icons/fi";
import axios from "axios";
import VoiceAssistant from "../voice-assistant/VoiceAssistant";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:10000";

const SUGGESTIONS = [
  "Who led the Ethiopian army at Adwa?",
  "Where did the Battle of Adwa take place?",
  "Why was Adwa important for Africa?",
  "What role did Empress Taytu play?",
  "What was Ras Alula Aba Nega's role in the Battle of Adwa?",
];

/* =========================
   ANSWER PARSING
========================= */

// Grab one section, stopping at the next **Heading:** or the end of the text.
function section(text, label) {
  const re = new RegExp(
    `\\*\\*${label}:\\*\\*\\s*([\\s\\S]*?)(?=\\n\\s*\\*\\*[A-Za-z ]+:\\*\\*|$)`,
    "i"
  );
  const match = text.match(re);
  return match ? match[1].trim() : "";
}

function parseAnswer(text) {
  return {
    title: section(text, "Title"),
    summary: section(text, "Summary"),
    details: section(text, "Details"),
    // Split on line breaks only, then strip one leading bullet marker. Splitting
    // on "-" would break hyphenated words such as Italo-Ethiopian and 1895-1896.
    keyFacts: section(text, "Key Facts")
      .split(/\r?\n/)
      .map((line) => line.replace(/^\s*(?:[-*•–—]|\d+[.)])\s*/, "").trim())
      .filter(Boolean),
  };
}

// "short historical note-2.pdf" -> "Short historical note 2"
function prettySource(name) {
  const base = String(name).replace(/^.*[\\/]/, "").replace(/\.pdf$/i, "");
  const words = base.replace(/[_-]+/g, " ").replace(/\s+/g, " ").trim();
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/* =========================
   AI ANSWER
========================= */
function AIAssistantAnswer({ text, sources }) {
  const { title, summary, details, keyFacts } = parseAnswer(text);
  const showSources =
    sources && sources.length > 0 && sources[0].toLowerCase() !== "none";

  return (
    <div>
      {title && <div className={styles.aiTitle}>{title}</div>}
      {summary && <div className={styles.aiSummary}>{summary}</div>}
      {details && <div className={styles.aiDetails}>{details}</div>}

      {keyFacts.length > 0 && (
        <ul className={styles.aiKeyFacts}>
          {keyFacts.map((fact, i) => (
            <li key={i}>{fact}</li>
          ))}
        </ul>
      )}

      {showSources && (
        <div className={styles.sources}>
          <span className={styles.sourcesLabel}>Sources</span>
          <span className={styles.sourceChips}>
            {/* Plain labels, not links: these are local document names, and a
                bare filename in href resolves to a dead in-app URL. */}
            {sources.map((src, i) => (
              <span key={i} className={styles.sourceChip} title={src}>
                {prettySource(src)}
              </span>
            ))}
          </span>
        </div>
      )}
    </div>
  );
}

/* =========================
   COPY BUTTON
========================= */
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard blocked (insecure origin or denied permission) - stay silent.
    }
  };

  return (
    <button
      type="button"
      className={styles.copyButton}
      onClick={copy}
      aria-label={copied ? "Answer copied" : "Copy answer"}
      title={copied ? "Copied" : "Copy answer"}
    >
      {copied ? <FiCheck size={14} /> : <FiCopy size={14} />}
    </button>
  );
}

/* =========================
   ERROR MESSAGES
========================= */
// Turn an axios failure into something a person can act on. The backend now
// distinguishes warmup (503) from overload (429), so stop flattening every
// failure into "Server error".
function describeError(err) {
  if (err.code === "ECONNABORTED" || /timeout/i.test(err.message || "")) {
    return "That took longer than usual. The assistant may still be starting up.";
  }

  if (!err.response) {
    return "Could not reach the server. Check your connection and try again.";
  }

  const { status, data } = err.response;

  if (status === 503) {
    return data?.error || "Adwa AI is still starting up. Give it a moment.";
  }
  if (status === 429) {
    return "Too many questions at once. Wait a few seconds and try again.";
  }
  if (status === 400) {
    return data?.error || "That message could not be sent.";
  }

  return "Something went wrong on the server. Please try again.";
}

/* =========================
   MAIN CHAT COMPONENT
========================= */
const Body = ({ onInputFocus, onInputBlur, resetSignal }) => {
  const [chat, setChat] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [lastMessage, setLastMessage] = useState("");
  const [warmingUp, setWarmingUp] = useState(false);

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  /* AUTO SCROLL */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chat, loading]);

  /* RESET ON NEW CHAT */
  useEffect(() => {
    setChat([]);
    setInput("");
    setLoading(false);
    setError("");
    setLastMessage("");
    if (inputRef.current) {
      inputRef.current.textContent = "";
    }
  }, [resetSignal]);

  /* READINESS - tell the user the backend is waking rather than letting the
     first question fail silently. */
  useEffect(() => {
    let cancelled = false;
    let timer;

    const check = async () => {
      try {
        await axios.get(`${API_URL}/ready`, { timeout: 8000 });
        if (!cancelled) setWarmingUp(false);
      } catch {
        if (cancelled) return;
        setWarmingUp(true);
        timer = setTimeout(check, 4000);
      }
    };

    check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  const send = useCallback(async (message) => {
    if (!message || loading) return;

    setChat((prev) => [...prev, { text: message, sender: "user" }]);
    setLastMessage(message);
    setInput("");
    if (inputRef.current) {
      inputRef.current.textContent = "";
    }

    setLoading(true);
    setError("");

    try {
      const res = await axios.post(
        `${API_URL}/chat`,
        { message },
        { timeout: 60000 }
      );

      setWarmingUp(false);
      setChat((prev) => [
        ...prev,
        {
          text: res.data?.response || "No response from server.",
          sender: "ai",
          sources: res.data?.sources || [],
        },
      ]);
    } catch (err) {
      console.error("Chat error:", err);
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  }, [loading]);

  const handleSend = () => send(input.trim());

  const handleRetry = () => {
    if (!lastMessage) return;
    setError("");
    // Drop the unanswered question so it is not duplicated in the transcript.
    setChat((prev) => {
      const last = prev[prev.length - 1];
      return last && last.sender === "user" ? prev.slice(0, -1) : prev;
    });
    send(lastMessage);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = (e) => {
    setInput(e.currentTarget.textContent || "");
  };

  const showWelcome = chat.length === 0 && !loading;

  return (
    <main className={styles.body}>
      {warmingUp && (
        <div className={styles.warmupBanner} role="status">
          Waking up the assistant, this can take a moment on first load.
        </div>
      )}

      {/* CHAT AREA - the welcome panel lives inside it so it can never sit
          underneath the fixed input bar. */}
      <div
        className={styles.chatContainer}
        role="log"
        aria-live="polite"
        aria-label="Conversation"
      >
        {showWelcome && (
          <div className={styles.welcomeMessage}>
            <h2>How can I help you today?</h2>
            <p>Ask anything about the Battle of Adwa and Ethiopian history.</p>

            <div className={styles.suggestions}>
              {SUGGESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  className={styles.suggestionChip}
                  onClick={() => send(question)}
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        )}

        {chat.map((msg, idx) => {
          const isUser = msg.sender === "user";

          if (isUser) {
            return (
              <div key={idx} className={styles.userMessageContainer}>
                <div className={styles.userBubble}>{msg.text}</div>
                <div className={styles.userEmoji} aria-hidden="true">🧑</div>
              </div>
            );
          }

          return (
            <div key={idx} className={styles.aiMessageContainer}>
              <div className={styles.assistantEmoji} aria-hidden="true">🤖</div>
              <div className={styles.aiBubble}>
                {/\*\*Title:\*\*/.test(msg.text) ? (
                  <AIAssistantAnswer text={msg.text} sources={msg.sources} />
                ) : (
                  <span>{msg.text}</span>
                )}
                <div className={styles.messageActions}>
                  <CopyButton text={msg.text} />
                </div>
              </div>
            </div>
          );
        })}

        {loading && (
          <div className={styles.aiMessageContainer}>
            <div className={styles.assistantEmoji} aria-hidden="true">🤖</div>
            <div className={styles.typingBubble} aria-label="Adwa AI is thinking">
              <span className={styles.dot} />
              <span className={styles.dot} />
              <span className={styles.dot} />
            </div>
          </div>
        )}

        {error && (
          <div className={styles.errorCard} role="alert">
            <span>{error}</span>
            {lastMessage && (
              <button
                type="button"
                className={styles.retryButton}
                onClick={handleRetry}
              >
                <FiRefreshCw size={14} /> Try again
              </button>
            )}
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* INPUT AREA */}
      <div className={styles.inputAreaRow}>
        <div
          className={styles.inputWrapper}
          onFocus={onInputFocus}
          onBlur={onInputBlur}
        >
          <div
            ref={inputRef}
            className={styles.inputField}
            contentEditable={!loading}
            suppressContentEditableWarning
            role="textbox"
            aria-multiline="true"
            aria-label="Ask a question about the Battle of Adwa"
            data-placeholder="Ask anything about Adwa..."
            onInput={handleInput}
            onKeyDown={handleKeyDown}
          />

          {!input.trim() && (
            <div className={styles.voiceBarWrapper}>
              <VoiceAssistant
                loading={loading}
                onVoiceInput={(text) => {
                  setInput(text);
                  if (inputRef.current) {
                    inputRef.current.textContent = text;
                  }
                }}
              />
            </div>
          )}

          <button
            className={styles.sendButton}
            onClick={handleSend}
            aria-label="Send message"
            title="Send"
            disabled={loading || !input.trim()}
          >
            <FiSend size={20} />
          </button>
        </div>

        <div className={styles.inputHint}>
          Enter to send, Shift + Enter for a new line
        </div>
      </div>
    </main>
  );
};

export default Body;
