import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { createReferral, listReferrals } from '../api/referrals'
import { emptyReferral } from '../api/types'
import type { Referral } from '../api/types'
import { ReferralForm } from '../components/ReferralForm'

export function ReferralInboxPage() {
  const [referrals, setReferrals] = useState<Referral[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const navigate = useNavigate()
  const [draft, setDraft] = useState({ ...emptyReferral })
  useEffect(() => {
    const controller = new AbortController()
    listReferrals(controller.signal).then(data => {
      if (!controller.signal.aborted) { setReferrals(data); setLoading(false) }
    }).catch(err => {
      if (!controller.signal.aborted) { setError(errorMessage(err)); setLoading(false) }
    })
    return () => controller.abort()
  }, [attempt])
  return <>
    <div className="page-heading"><div><p className="eyebrow">Synthetic cardiology intake</p><h1>Referral inbox</h1><p>Register a referral, attach its documents, and review the source evidence.</p></div></div>
    <div className="inbox-grid">
      <section className="card" aria-labelledby="inbox-title">
        <h2 id="inbox-title">Registered referrals</h2>
        {loading && <p role="status">Loading referrals…</p>}
        {error && <div role="alert"><p className="error">{error}</p><button onClick={() => { setError(''); setLoading(true); setAttempt(x => x + 1) }}>Retry list</button></div>}
        {!loading && !error && referrals.length === 0 && <p>No referrals yet. Create your first synthetic case.</p>}
        <ul className="referral-list">{[...referrals].reverse().map(referral => <li key={referral.id}>
          <Link to={`/referrals/${referral.id}`}>{referral.patient_name}</Link>
          <span>Cardiology · {new Date(referral.created_at).toLocaleString()}</span>
        </li>)}</ul>
      </section>
      <section className="card" aria-labelledby="create-title"><h2 id="create-title">Create referral</h2><p>Enter the five required fields, then attach the referral packet.</p>
        <ReferralForm value={draft} onChange={setDraft} onSave={async data => { const referral = await createReferral(data); navigate(`/referrals/${referral.id}`) }} />
      </section>
    </div>
  </>
}
