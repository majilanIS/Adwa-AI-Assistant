import React, { useState, useRef, useEffect } from "react";
import styles from "./Body.module.css";
import { FiSend } from "react-icons/fi";
import axios from "axios";
import VoiceAssistant from "../voice-assistant/VoiceAssistant";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:1986";

/* =========================
   AI ANSWER FORMATTER
========================= */
function AIAssistantAnswer({ text, sources }) {

  const titleMatch = text.match(/\*\*Title:\*\*\s*([^\n]+)/i);
  const summaryMatch = text.match(/\*\*Summary:\*\*\s*([^\n]+)/i);
  const detailsMatch = text.match(/\*\*Details:\*\*\s*([\s\S]*?)(?=\*\*Key Facts|\*\*Sources|\s*$)/i);
  const keyFactsMatch = text.match(/\*\*Key Facts:\*\*\s*([\s\S]*?)(?=\*\*Sources|\s*$)/i);

  let keyFacts = [];
  if (keyFactsMatch && keyFactsMatch[1]) {
    keyFacts = keyFactsMatch[1]
      .split(/\n|•|\-/)
      .map((fact) => fact.trim())
      .filter((fact) => fact.length > 0);
  }

  const showSources = sources && sources.length > 0 && sources[0].toLowerCase() !== "none";

  return (
    <div>

      {titleMatch && <div className={styles.aiTitle}>{titleMatch[1]}</div>}

      {summaryMatch && <div className={styles.aiSummary}>{summaryMatch[1]}</div>}

      {detailsMatch && <div className={styles.aiDetails}>{detailsMatch[1]}</div>}

      {keyFacts.length > 0 && (
        <div className={styles.aiKeyFacts}>
          {keyFacts.map((fact, i) => (
            <div key={i}>• {fact}</div>
          ))}
        </div>
      )}

      {showSources && (
        <div className={styles.sources}>
          <strong>Sources:</strong>{" "}
          {sources.map((src, i) => (
            <span key={i}>
              <a href={src} target="_blank" rel="noopener noreferrer">
                {src}
              </a>
              {i < sources.length - 1 ? ", " : ""}
            </span>
          ))}
        </div>
      )}

    </div>
  );
}

/* =========================
   MAIN CHAT COMPONENT
========================= */
const Body = ({ onInputFocus, onInputBlur }) => {

  const [chat, setChat] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  /* =========================
     AUTO SCROLL
  ========================= */
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat]);

  /* =========================
     SEND MESSAGE
  ========================= */
  const handleSend = async () => {

    const message = input.trim();

    if (!message || loading) return;

    setChat(prev => [
      ...prev,
      { text: message, sender: "user" }
    ]);

    setInput("");

    if (inputRef.current) {
      inputRef.current.textContent = "";
    }

    setLoading(true);
    setError("");

    try {

      const res = await axios.post(`${API_URL}/chat`, {
        message: message
      });

      const aiResponse = res.data?.response || "No response from server.";

      setChat(prev => [
        ...prev,
        {
          text: aiResponse,
          sender: "ai",
          sources: res.data?.sources || []
        }
      ]);

    } catch (err) {

      console.error("Chat error:", err);

      setError("Server error or timeout. Please try again.");

      setChat(prev => [
        ...prev,
        { text: "Server error. Try again.", sender: "ai" }
      ]);

    } finally {

      setLoading(false);

    }

  };

  /* =========================
     ENTER KEY SEND
  ========================= */
  const handleKeyDown = (e) => {

    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }

  };

  /* =========================
     INPUT CHANGE
  ========================= */
  const handleInput = (e) => {
    const value = e.currentTarget.textContent || "";
    setInput(value);
  };

  const showWelcome = chat.length === 0;
  return (
    <main className={styles.body}>
      {/* Only the centered welcome message remains */}
      {showWelcome && (
        <div className={styles.welcomeMessage}>
          <h2>How can I help you today?</h2>
          <p>Ask anything about Adwa, history, or get started with a new chat below.</p>
        </div>
      )}
      {/* CHAT AREA */}
      <div className={styles.chatContainer}>
        {chat.map((msg, idx) => {
          const isUser = msg.sender === "user";
          return (
            <div
              key={idx}
              className={
                isUser
                  ? styles.userMessageContainer
                  : styles.aiMessageContainer
              }
            >
              {/* Emoji and message bubble */}
              {isUser ? (
                <>
                  <div className={styles.userEmoji}>🧑</div>
                  <div className={styles.userBubble}>{msg.text}</div>
                </>
              ) : (
                <>
                  <div className={styles.assistantEmoji}>🤖</div>
                  <div className={styles.aiBubble}>
                    {/\*\*Title:\*\*/.test(msg.text) ? (
                      <AIAssistantAnswer text={msg.text} sources={msg.sources} />
                    ) : (
                      <span>{msg.text}</span>
                    )}
                  </div>
                </>
              )}
            </div>
          );
        })}
        <div ref={chatEndRef} />
        {loading && (
          <div className={styles.overlaySpinner}>
            <div className={styles.loadingText}>
              Thinking...
            </div>
          </div>
        )}
        {error && (
          <div className={styles.overlayError}>
            {error}
          </div>
        )}
      </div>
      {/* INPUT AREA FIXED AT BOTTOM */}
      <div className={styles.inputAreaRow}>
        <div
          className={styles.inputWrapper}
          onFocus={onInputFocus}
          onBlur={onInputBlur}
        >
          {/* Editable input field */}
          <div
            ref={inputRef}
            className={styles.inputField}
            contentEditable={!loading}
            suppressContentEditableWarning
            role="textbox"
            aria-multiline="true"
            data-placeholder="Ask anything about Adwa..."
            onInput={handleInput}
            onKeyDown={handleKeyDown}
          />
          {/* VOICE BAR — shows only when input is empty */}
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
          {/* SEND BUTTON */}
          <button
            className={styles.sendButton}
            onClick={handleSend}
            aria-label="Send"
            disabled={loading}
          >
            <FiSend size={20} />
          </button>
        </div>
      </div>
      {/* STATUS BELOW INPUT */}
      {loading && (
        <div className={styles.belowInputSpinner}>
          <div className={styles.loadingText}>
            Thinking...
          </div>
        </div>
      )}
      {error && (
        <div className={styles.belowInputError}>
          {error}
        </div>
      )}
    </main>
  );
};

export default Body;