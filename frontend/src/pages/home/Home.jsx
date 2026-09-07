import React from "react";

import Header from "../../components/header/Header";
import Body from "../../components/body/Body";
import Footer from "../../components/footer/Footer";
import axios from "axios";
import styles from "./Home.module.css";
// import VoiceAssistantBar from "../../components/voice-assistant/VoiceAssistantBar";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:10000";

const Home = () => {
  const [resetCounter, setResetCounter] = React.useState(0);

  const handleNewChat = async () => {
    try {
      await axios.post(`${API_URL}/new-chat`);
    } catch (error) {
      // Clearing server-side history is best effort; the local transcript is
      // reset either way so the button always does something visible.
      console.error("New chat failed:", error);
    }
    setResetCounter((prev) => prev + 1);
  };

  return (
    <div className={styles.home}>
      <Header onNewChat={handleNewChat} />
      <div className={styles.bodyContainer}>
        <Body resetSignal={resetCounter} />
      </div>
      <Footer />
    </div>
  );
};

export default Home;