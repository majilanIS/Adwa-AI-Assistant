import React from "react";
import styles from "./Footer.module.css";

const Footer = () => {
  return (
    <footer className={styles.footer}>
      <p className={styles.footerText}>© 2026 Adwa AI Assistant.</p>
      <p className={styles.footerText}>Adwa AI can make mistakes. Check important information.</p>
    </footer>
  );
};

export default Footer;