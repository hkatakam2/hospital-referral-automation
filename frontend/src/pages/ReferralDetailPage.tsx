import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { updateReferral } from '../api/referrals'
import { fieldLabels, fieldNames } from '../api/types'
import type { FieldName, Referral, ReferralInput } from '../api/types'
import { ReferralForm } from '../components/ReferralForm'
import { WorkflowPanel } from '../components/WorkflowPanel'
import { DocumentPanel } from '../components/DocumentPanel'
import { ExtractionPanel } from '../components/ExtractionPanel'
import { useReferralWorkspace } from '../hooks/useReferralWorkspace'
import type { ReferralWorkspace } from '../hooks/useReferralWorkspace'

export function ReferralDetailPage() {
  const { referralId = '' } = useParams()
  return <ReferralDetail key={referralId} id={referralId} />
}

function ReferralDetail({ id }: { id: string }) {
  const workspace = useReferralWorkspace(id)
  const { referral } = workspace
  return <>
    <Link className="back-link" to="/referrals">← Referral inbox</Link>
    {referral.error && <div role="alert"><p className="error">{referral.error}</p><button onClick={referral.refresh}>Retry referral</button></div>}
    {!referral.data ? <p role="status">Loading referral…</p>
      : <ReviewWorkspace key={referral.data.id} referral={referral.data} workspace={workspace} />}
  </>
}

function ReviewWorkspace({ referral, workspace }: { referral: Referral; workspace: ReferralWorkspace }) {
  const [saved, setSaved] = useState(referral)
  const [draft, setDraft] = useState<ReferralInput>({ ...referral })
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)
  const dirty = fieldNames.some(field => draft[field] !== saved[field])
  function useCandidate(field: FieldName, value: string) {
    setDraft(current => ({ ...current, [field]: value }))
    setNotice(`${fieldLabels[field]} copied into correction draft. Save corrections to persist it.`)
  }
  async function save(data: ReferralInput) {
    const changes = Object.fromEntries(fieldNames.filter(field => data[field] !== saved[field]).map(field => [field, data[field]]))
    setSaving(true)
    try {
      const result = await updateReferral(saved.id, changes)
      setSaved(result); setDraft({ ...result }); setNotice('Corrections saved.')
    } finally { setSaving(false) }
  }
  return <>
    <div className="page-heading"><p className="eyebrow">Cardiology referral</p><h1>{saved.patient_name}</h1><p className="identifier">{saved.id}</p></div>
    <div className="workspace-grid">
      <div className="stack"><DocumentPanel workspace={workspace} /></div>
      <div className="stack">
        <section className="card" aria-labelledby="corrections-title">
          <h2 id="corrections-title">Saved referral and corrections</h2>
          <dl className="saved-values">{fieldNames.map(field => <div key={field}><dt>{fieldLabels[field]}</dt><dd>{saved[field]}</dd></div>)}</dl>
          <h3>Correction draft</h3>
          <p>Edits change the registered referral. Historical extraction findings remain unchanged.</p>
          {dirty && <p className="warning">You have unsaved corrections.</p>}
          {notice && <p role="status" className="success">{notice}</p>}
          <ReferralForm value={draft} onChange={value => { setDraft(value); setNotice('') }} onSave={save} submitLabel="Save corrections" />
        </section>
        <WorkflowPanel workspace={workspace} />
        <ExtractionPanel workspace={workspace} onUse={useCandidate} saving={saving} />
      </div>
    </div>
  </>
}
