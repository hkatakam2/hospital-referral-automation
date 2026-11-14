import { useState } from 'react'
import type { FormEvent } from 'react'
import { workflowLabels } from '../api/types'
import type { ReferralWorkspace } from '../hooks/useReferralWorkspace'

export function WorkflowPanel({ workspace: w, dirty, savedValuesVersion }: {
  workspace: ReferralWorkspace; dirty: boolean; savedValuesVersion: number
}) {
  const [reviewer, setReviewer] = useState('')
  const [reason, setReason] = useState('')
  const [information, setInformation] = useState('')
  const [linkExtraction, setLinkExtraction] = useState(false)
  const [notice, setNotice] = useState('')
  const [intent, setIntent] = useState<'request' | 'ready'>('request')
  const referral = w.referral.data
  if (!referral) return null
  const status = referral.status ?? 'received'
  const action = status === 'ready' ? 'reopen' : status === 'missing_information' ? 'resume' : intent
  const requesting = action === 'request'
  const labels = { request: 'Record missing-information request', resume: 'Resume review',
    ready: 'Mark ready for downstream processing', reopen: 'Reopen review' }
  const readyBlocked = dirty || w.corrections.pending || w.upload.pending || w.runExtraction.pending ||
    w.refreshCorrections.pending || w.documents.loading || !!w.documents.error ||
    w.runs.loading || !!w.runs.error || w.extraction.loading || !!w.extraction.error ||
    !w.selectedExtraction?.complete || w.sourcesChanged ||
    w.selectedExtraction?.id !== w.runs.data?.[0]?.id ||
    savedValuesVersion !== referral.values_version
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!referral) return
    setNotice('')
    const command = {
      reviewer, reason, expected_workflow_version: referral.workflow_version,
      ...(action === 'ready' && w.selectedExtraction ? { extraction_id: w.selectedExtraction.id, expected_values_version: savedValuesVersion } : {}),
      ...(requesting ? {
        requested_information: information,
        ...(linkExtraction && w.selectedExtraction ? { extraction_id: w.selectedExtraction.id } : {}),
      } : {}),
    }
    const result = await w.workflow.execute(action, command)
    if (result) {
      setReason(''); setInformation(''); setLinkExtraction(false)
      setNotice({ request: 'Missing-information request recorded.', resume: 'Review resumed.', ready: 'Ready decision recorded.', reopen: 'Review reopened.' }[action])
    }
  }
  return <section className="card workflow-panel" aria-labelledby="workflow-title">
    <h2 id="workflow-title">Coordinator workflow</h2>
    <p role="status">Referral status: <strong>{workflowLabels[status]}</strong></p>
    <p>Record a request here, then contact the referring organization separately. This application does not send messages.</p>
    <p>Uploading documents, running extraction, and saving corrections do not close a request. Resume review explicitly when ready.</p>
    <form onSubmit={submit}>
      <fieldset disabled={w.workflow.pending || w.referral.loading}>
        <legend>Record a workflow action</legend>
        {status !== 'ready' && status !== 'missing_information' && <>
          <label htmlFor="workflow-action">Workflow action</label>
          <select id="workflow-action" value={intent} onChange={e => { setIntent(e.target.value as 'request' | 'ready'); setNotice('') }}>
            <option value="request">Request missing information</option>
            <option value="ready">Mark ready for downstream processing</option>
          </select>
        </>}
        {action === 'ready' && <>
          <p>Review the latest extraction and save corrections before recording this administrative decision. This is not clinical approval.</p>
          {readyBlocked && <p className="warning">Ready requires a satisfied latest checklist covering all attachments, saved corrections, and completed refreshes.</p>}
        </>}
        {action === 'reopen' && <p>Reopen review before attaching documents or saving corrections. The previous ready decision stays in history.</p>}
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
        <button type="submit" disabled={action === 'ready' && readyBlocked}>{w.workflow.pending ? 'Recording action…' : labels[action]}</button>
      </fieldset>
    </form>
    {w.workflow.error && <p role="alert" className="error">{w.workflow.error}</p>}
    {notice && <p role="status" className="success">{notice}</p>}
    <div className="section-toolbar"><h3>Workflow history</h3><button disabled={w.workflow.pending || w.reviewEvents.loading || w.referral.loading} onClick={() => { w.referral.refresh(); w.reviewEvents.refresh() }}>Refresh workflow</button></div>
    {w.reviewEvents.loading && <p role="status">Loading workflow history…</p>}
    {w.reviewEvents.error && <p role="alert" className="error">{w.reviewEvents.error} Refresh workflow to recover history.</p>}
    {w.reviewEvents.data?.length === 0 && <p>No coordinator workflow actions recorded.</p>}
    <ol className="workflow-events">{w.reviewEvents.data?.map(event => <li key={event.id}>
      <strong>{{ request_missing_information: 'Missing information requested', resume_review: 'Review resumed', mark_ready: 'Ready for downstream processing', reopen_review: 'Review reopened' }[event.action]}</strong>
      <p>{workflowLabels[event.previous_status]} → {workflowLabels[event.new_status]}</p>
      <p>{event.reviewer} (supplied demo identity) · {new Date(event.created_at).toLocaleString()}</p>
      {event.requested_information && <p>Information needed: {event.requested_information}</p>}
      <p>Reason: {event.reason}</p>
      {event.reviewed_values_version != null && <p>Reviewed saved values version: {event.reviewed_values_version}</p>}
      {event.extraction_id && <button onClick={() => w.selectRun(event.extraction_id!)}>View referenced extraction</button>}
    </li>)}</ol>
  </section>
}
