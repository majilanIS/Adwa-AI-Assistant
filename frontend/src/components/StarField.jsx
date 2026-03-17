// StarField.jsx
import React, { useEffect, useRef } from "react";

const STAR_COUNT = 80;
const STAR_COLORS = ["#fff", "#ffe9c4", "#d4fbff"];

function randomBetween(a, b) {
  return a + Math.random() * (b - a);
}

const StarField = () => {
  const canvasRef = useRef(null);
  const animationRef = useRef();
  const stars = useRef([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let width = window.innerWidth;
    let height = window.innerHeight;
    canvas.width = width;
    canvas.height = height;

    // Generate stars
    stars.current = Array.from({ length: STAR_COUNT }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      r: randomBetween(0.7, 2.2),
      color: STAR_COLORS[Math.floor(Math.random() * STAR_COLORS.length)],
      speed: randomBetween(0.05, 0.25),
      twinkle: Math.random() * Math.PI * 2,
    }));

    function animate() {
      ctx.clearRect(0, 0, width, height);
      for (let star of stars.current) {
        // Twinkle effect
        const twinkle = 0.5 + 0.5 * Math.sin(star.twinkle + Date.now() * 0.001 * star.speed * 2);
        ctx.globalAlpha = twinkle;
        ctx.beginPath();
        ctx.arc(star.x, star.y, star.r, 0, 2 * Math.PI);
        ctx.fillStyle = star.color;
        ctx.shadowColor = star.color;
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
        // Move star
        star.y += star.speed;
        if (star.y > height) {
          star.y = 0;
          star.x = Math.random() * width;
        }
      }
      ctx.globalAlpha = 1;
      animationRef.current = requestAnimationFrame(animate);
    }
    animate();

    function handleResize() {
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width;
      canvas.height = height;
    }
    window.addEventListener("resize", handleResize);
    return () => {
      cancelAnimationFrame(animationRef.current);
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
};

export default StarField;
