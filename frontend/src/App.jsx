import { useState } from 'react'
import './App.css'
import Home from './pages/home/Home'
import StarField from './components/StarField'

function App() {

  const [showWelcome, setShowWelcome] = useState(true)

  // Handler to hide welcome when user types
  const handleInputFocus = () => {
    setShowWelcome(false)
  }
  const handleInputBlur = () => {
    setShowWelcome(false)
  }

  const handleNewChat = () => {
    setShowWelcome(true)
  }

  return (
    <>
      <StarField />
      {showWelcome && (
        <div style={{
          position: 'fixed',
          top: '90px',
          left: 0,
          width: '100vw',
          textAlign: 'center',
          zIndex: 10,
          color: '#fff',
          fontSize: '1.5rem',
          fontWeight: 600,
          letterSpacing: '0.02em',
          textShadow: '0 2px 16px #000',
          pointerEvents: 'none',
          transition: 'opacity 0.5s',
        }}>
        </div>
      )}
      <Home onInputFocus={handleInputFocus} onInputBlur={handleInputBlur} onNewChat={handleNewChat} />
    </>
  )
}

export default App
