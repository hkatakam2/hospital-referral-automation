import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { errorMessage } from '../api/client'
import { getReferral, updateReferral } from '../api/referrals'
import { fieldNames } from '../api/types'
import type { Referral, ReferralInput } from '../api/types'
import { ReferralForm } from '../components/ReferralForm'

export function ReferralDetailPage() {
  const { referralId = '' } = useParams()
  return <ReferralDetail key={referralId} id={referralId} />
}

function ReferralDetail({ id }: { id: string }) {
  const [referral, setReferral] = useState<Referral | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [saved, setSaved] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    getReferral(id, controller.signal).then(value => {
      if (!controller.signal.aborted) setReferral(value)
    }).catch(err => { if (!controller.signal.aborted) setError(errorMessage(err)) })
    return () => controller.abort()
  }, [id, attempt])
  async function save(draft: ReferralInput) {
    if (!referral) return
    const changes = Object.fromEntries(fieldNames.filter(field => draft[field] !== referral[field]).map(field => [field, draft[field]]))
    const result = await updateReferral(id, changes)
    setReferral(result); setSaved(true)
  }
  return <>
    <Link className="back-link" to="/referrals">← Referral inbox</Link>
    {error ? <div role="alert"><p className="error">{error}</p><button onClick={() => { setError(''); setAttempt(x => x + 1) }}>Retry referral</button></div>
      : !referral ? <p role="status">Loading referral…</p> : <>
        <div className="page-heading"><p className="eyebrow">Cardiology referral</p><h1>{referral.patient_name}</h1><p className="identifier">{referral.id}</p></div>
        <section className="card"><h2>Saved referral values</h2><p>Corrections change the registered referral.</p>
          {saved && <p role="status" className="success">Corrections saved.</p>}
          <ReferralForm key={JSON.stringify(referral)} initial={referral} onSave={save} submitLabel="Save corrections" />
        </section>
      </>}
  </>
}
