import React from "react";
import styles from "./Header.module.css";

const Header = ({ onNewChat }) => {
  return (
    <header className={styles.header}>
      <div className={styles.headerFixedRow}>
        {/* Brand */}
        <div className={styles.brandFixed}>
          <h1>Adwa AI</h1>
          <span className={styles.tagline}>Historical Chat Assistant</span>
        </div>

        {/* Navigation */}
        <nav className={styles.navFixed}>
          <button className={styles.navItem} onClick={onNewChat}>
            New Chat
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Header;