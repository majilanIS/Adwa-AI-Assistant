import React, { useState, useRef } from "react";
import MicrophoneIcon from "./MicrophoneIcon";
import styles from "./VoiceAssistant.module.css";

const API_URL = "http://127.0.0.1:1986";

const VoiceAssistant = ({ onVoiceInput, loading }) => {

  const [listening, setListening] = useState(false);
  // Remove local response and userInput state, delegate to parent
  const [error, setError] = useState("");

  const recognitionRef = useRef(null);

  const startListening = () => {

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert("Your browser does not support voice recognition. Please use Chrome.");
    return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognitionRef.current = recognition;

    recognition.start();
    setListening(true);

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      setError("");
      setListening(false);
      if (onVoiceInput) {
        onVoiceInput(text);
      }
    };

    recognition.onerror = () => {

      setListening(false);
      setError("Speech recognition failed. Please try again.");

    };

    recognition.onend = () => {
      setListening(false);
    };

  };

  const stopListening = () => {

    recognitionRef.current?.stop();
    setListening(false);

  };

  return (
    <div className={styles.voiceAssistantContainer}>
      <button
        className={`${styles.microphone_btn} ${listening ? styles.listening : ""}`}
        onClick={() => {
          if (listening) {
            stopListening();
          } else if (error) {
            setError("");
            startListening();
          } else {
            startListening();
          }
        }}
      >
        <MicrophoneIcon size={22} />
      </button>


      {listening && !error && !loading && (
        <div className={styles.waveContainer}>
          <span></span>
          <span></span>
          <span></span>
          <span></span>
        </div>
      )}

      {error && (
        <div className={styles.error_message}>{error}</div>
      )}
    </div>
  );
};

export default VoiceAssistant;