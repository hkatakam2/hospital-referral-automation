import { useEffect, useState } from 'react'
import { getHealth } from './api'

type Connection = 'checking' | 'connected' | 'unavailable'

export default function App() {
  const [connection, setConnection] = useState<Connection>('checking')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 5000)
    let active = true

    getHealth(controller.signal)
      .then(() => { if (active) setConnection('connected') })
      .catch(() => { if (active) setConnection('unavailable') })
      .finally(() => window.clearTimeout(timeout))

    return () => {
      active = false
      window.clearTimeout(timeout)
      controller.abort()
    }
  }, [attempt])

  return (
    <main>
      <header><span className="mark" aria-hidden="true">+</span> Referral workspace</header>
      <section className="intro">
        <p className="eyebrow">Hospital referral automation</p>
        <h1>A foundation for<br />better connected care.</h1>
        <p className="description">Your workspace is ready to build. Start connecting referral workflows, care teams, and the information they need.</p>
      </section>
      <section className="status-card" aria-labelledby="connection-heading">
        <div>
          <p className="eyebrow">System connection</p>
          <h2 id="connection-heading">Backend API</h2>
          <p role="status" className={`status ${connection}`}>
            <span className="dot" aria-hidden="true" />
            {connection === 'checking' ? 'Checking connection…' : connection === 'connected' ? 'Connected and ready' : 'Unable to reach the API. Check that the backend is running.'}
          </p>
        </div>
        <button disabled={connection === 'checking'} onClick={() => {
          setConnection('checking')
          setAttempt((value) => value + 1)
        }}>Check connection <span aria-hidden="true">↗</span></button>
      </section>
      <footer>Hospital Referral Automation · Development workspace</footer>
    </main>
  )
}
