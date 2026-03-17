import React from "react";

import Header from "../../components/header/Header";
import Body from "../../components/body/Body";
import Footer from "../../components/footer/Footer";
import axios from "axios";
import styles from "./Home.module.css";
// import VoiceAssistantBar from "../../components/voice-assistant/VoiceAssistantBar";

const API_URL = "http://127.0.0.1:1986";

const Home = ({ onInputFocus, onInputBlur }) => {

  const handleNewChat = async () => {
    await axios.post(`${API_URL}/new-chat`);
    window.location.reload(); 
  };

  return (
    <div className={styles.home}>
      <Header onNewChat={handleNewChat} />
      <div className={styles.bodyContainer}>
        <Body onInputFocus={onInputFocus} onInputBlur={onInputBlur} />
      </div>
      <div>
      </div>
      <Footer />
    </div>
  );
};

export default Home;