import { useState } from 'react'
import SubmissionPage from './submission-page/SubmissionPage'
import './app-styles/common.scss'
function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="App">
      <SubmissionPage />
    </div>
  )
}

export default App
