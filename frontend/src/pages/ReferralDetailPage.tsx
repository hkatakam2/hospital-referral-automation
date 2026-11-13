import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
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
  const [reviewer, setReviewer] = useState('')
  const [reason, setReason] = useState('')
  const saving = workspace.corrections.pending
  const dirty = fieldNames.some(field => draft[field] !== saved[field])
  function useCandidate(field: FieldName, value: string) {
    setDraft(current => ({ ...current, [field]: value }))
    setNotice(`${fieldLabels[field]} copied into correction draft. Save corrections to persist it.`)
  }
  async function save(data: ReferralInput) {
    const changes = Object.fromEntries(fieldNames.filter(field => data[field] !== saved[field]).map(field => [field, data[field]]))
    if (!reviewer.trim()) throw new Error('Enter a nonblank correction reviewer.')
    if (!reason.trim()) throw new Error('Enter a nonblank reason for corrections.')
    setNotice('')
    const result = await workspace.corrections.execute({
      ...changes, reviewer, reason, expected_values_version: saved.values_version,
    })
    if (result) {
      setSaved(result); setDraft({ ...result }); setReason('')
      setNotice(Object.keys(changes).length ? 'Corrections saved.' : 'No values changed.')
    }
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
          <ReferralForm value={draft} onChange={value => { setDraft(value); setNotice('') }} onSave={save} submitLabel="Save corrections" disabled={workspace.refreshCorrections.pending}>
            <label htmlFor="correction-reviewer">Correction reviewer (demo identity)</label>
            <input id="correction-reviewer" required maxLength={2000} value={reviewer} onChange={e => setReviewer(e.target.value)} />
            <p>This supplied name is not an authenticated identity.</p>
            <label htmlFor="correction-reason">Reason for corrections</label>
            <textarea id="correction-reason" required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} />
          </ReferralForm>
          <p>If a save conflicts or its response is interrupted, refresh corrections before retrying. Compare current saved values with your retained draft.</p>
          <button disabled={saving || workspace.refreshCorrections.pending} onClick={async () => {
            const result = await workspace.refreshCorrections.execute()
            if (result) {
              setSaved(result)
              setNotice('Saved values refreshed. Your draft is unchanged; compare it with the saved values before saving again.')
            }
          }}>Refresh corrections</button>
          {workspace.refreshCorrections.error && <p role="alert" className="error">{workspace.refreshCorrections.error}</p>}
        </section>
        <section className="card" aria-labelledby="correction-history-title">
          <h2 id="correction-history-title">Correction history</h2>
          <button disabled={workspace.correctionEvents.loading} onClick={workspace.correctionEvents.refresh}>Refresh correction history</button>
          {workspace.correctionEvents.loading && <p role="status">Loading correction history…</p>}
          {workspace.correctionEvents.error && <p role="alert" className="error">{workspace.correctionEvents.error} Refresh correction history to recover; saved corrections are not repeated.</p>}
          {workspace.correctionEvents.data?.length === 0 && <p>No correction events recorded. Earlier changes were not audited.</p>}
          <ol className="workflow-events">{workspace.correctionEvents.data?.map(event => <li key={event.id}>
            <strong>Saved values version {event.values_version}</strong>
            <p>{event.reviewer} (supplied demo identity) · {new Date(event.created_at).toLocaleString()}</p>
            <p>Reason: {event.reason}</p>
            <dl className="saved-values">{fieldNames.filter(field => event.changes[field]).map(field => <div key={field}>
              <dt>{fieldLabels[field]}</dt><dd>{event.changes[field]!.previous} → {event.changes[field]!.new}</dd>
            </div>)}</dl>
          </li>)}</ol>
        </section>
        <WorkflowPanel workspace={workspace} />
        <ExtractionPanel workspace={workspace} onUse={useCandidate} saving={saving} />
      </div>
    </div>
  </>
}
