import React from "react";
import { FiPlus } from "react-icons/fi";
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
          <button
            className={styles.navItem}
            onClick={onNewChat}
            title="Start a new chat"
            aria-label="Start a new chat"
          >
            <FiPlus size={17} aria-hidden="true" />
            <span className={styles.navItemLabel}>New Chat</span>
          </button>
        </nav>
      </div>
    </header>
  );
};

export default Header;