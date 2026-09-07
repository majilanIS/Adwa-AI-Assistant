import './App.css'
import Home from './pages/home/Home'
import StarField from './components/StarField'

function App() {

  // The welcome panel lives in Body, which shows it whenever the transcript is
  // empty. App previously tracked a duplicate showWelcome flag that only ever
  // rendered an empty div, so it is gone.
  return (
    <>
      <StarField />
      <Home />
    </>
  )
}

export default App
