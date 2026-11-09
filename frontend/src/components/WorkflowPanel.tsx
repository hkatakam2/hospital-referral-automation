import { useState } from 'react'
import type { FormEvent } from 'react'
import { workflowLabels } from '../api/types'
import type { ReferralWorkspace } from '../hooks/useReferralWorkspace'

export function WorkflowPanel({ workspace: w }: { workspace: ReferralWorkspace }) {
  const [reviewer, setReviewer] = useState('')
  const [reason, setReason] = useState('')
  const [information, setInformation] = useState('')
  const [linkExtraction, setLinkExtraction] = useState(false)
  const [notice, setNotice] = useState('')
  const referral = w.referral.data
  if (!referral) return null
  const status = referral.status ?? 'received'
  const requesting = status !== 'missing_information'
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!referral) return
    setNotice('')
    const command = {
      reviewer, reason, expected_workflow_version: referral.workflow_version,
      ...(requesting ? {
        requested_information: information,
        ...(linkExtraction && w.selectedExtraction ? { extraction_id: w.selectedExtraction.id } : {}),
      } : {}),
    }
    const result = await w.workflow.execute(requesting ? 'request' : 'resume', command)
    if (result) {
      setReason(''); setInformation(''); setLinkExtraction(false)
      setNotice(requesting ? 'Missing-information request recorded.' : 'Review resumed.')
    }
  }
  return <section className="card workflow-panel" aria-labelledby="workflow-title">
    <h2 id="workflow-title">Coordinator workflow</h2>
    <p role="status">Referral status: <strong>{workflowLabels[status]}</strong></p>
    <p>Record a request here, then contact the referring organization separately. This application does not send messages.</p>
    <p>Uploading documents, running extraction, and saving corrections do not close a request. Resume review explicitly when ready.</p>
    <form onSubmit={submit}>
      <fieldset disabled={w.workflow.pending || w.referral.loading}>
        <legend>{requesting ? 'Request missing information' : 'Resume review'}</legend>
        <label htmlFor="workflow-reviewer">Reviewer name (demo identity)</label>
        <input id="workflow-reviewer" required maxLength={2000} value={reviewer} onChange={e => setReviewer(e.target.value)} />
        <p>This supplied name is not an authenticated identity.</p>
        {requesting && <>
          <label htmlFor="workflow-information">Information needed</label>
          <textarea id="workflow-information" required maxLength={2000} value={information} onChange={e => setInformation(e.target.value)} />
          {w.selectedExtraction && <label className="workflow-checkbox">
            <input type="checkbox" checked={linkExtraction} onChange={e => setLinkExtraction(e.target.checked)} />
            Include the selected result as request context
          </label>}
        </>}
        <label htmlFor="workflow-reason">Reason for workflow action</label>
        <textarea id="workflow-reason" required maxLength={2000} value={reason} onChange={e => setReason(e.target.value)} />
        <button type="submit">{w.workflow.pending ? 'Recording action…' : requesting ? 'Record missing-information request' : 'Resume review'}</button>
      </fieldset>
    </form>
    {w.workflow.error && <p role="alert" className="error">{w.workflow.error}</p>}
    {notice && <p role="status" className="success">{notice}</p>}
    <div className="section-toolbar"><h3>Workflow history</h3><button disabled={w.workflow.pending || w.reviewEvents.loading || w.referral.loading} onClick={() => { w.referral.refresh(); w.reviewEvents.refresh() }}>Refresh workflow</button></div>
    {w.reviewEvents.loading && <p role="status">Loading workflow history…</p>}
    {w.reviewEvents.error && <p role="alert" className="error">{w.reviewEvents.error} Refresh workflow to recover history.</p>}
    {w.reviewEvents.data?.length === 0 && <p>No coordinator workflow actions recorded.</p>}
    <ol className="workflow-events">{w.reviewEvents.data?.map(event => <li key={event.id}>
      <strong>{event.action === 'request_missing_information' ? 'Missing information requested' : 'Review resumed'}</strong>
      <p>{workflowLabels[event.previous_status]} → {workflowLabels[event.new_status]}</p>
      <p>{event.reviewer} (supplied demo identity) · {new Date(event.created_at).toLocaleString()}</p>
      {event.requested_information && <p>Information needed: {event.requested_information}</p>}
      <p>Reason: {event.reason}</p>
      {event.extraction_id && <button onClick={() => w.selectRun(event.extraction_id!)}>View referenced extraction</button>}
    </li>)}</ol>
  </section>
}
