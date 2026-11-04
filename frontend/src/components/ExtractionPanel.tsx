import { fieldLabels, fieldNames } from '../api/types'
import type { FieldName } from '../api/types'
import type { ReferralWorkspace } from '../hooks/useReferralWorkspace'

export function ExtractionPanel({ workspace: w, onUse, saving }: {
  workspace: ReferralWorkspace; saving: boolean; onUse: (field: FieldName, value: string) => void
}) {
  const { pending, error } = w.runExtraction
  const result = w.selectedExtraction
  return <section className="card" aria-labelledby="extraction-title">
    <div className="section-toolbar"><h2 id="extraction-title">Extraction review</h2><button className="primary" onClick={() => w.runExtraction.execute()} disabled={pending || !w.documents.data?.length}>{pending ? 'Extracting…' : 'Run extraction'}</button></div>
    <p>Each run preserves the source findings. Review candidates before copying them into your correction draft.</p>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="section-toolbar"><h3>Saved run history</h3><button disabled={w.runs.loading} onClick={w.runs.refresh}>Refresh history</button></div>
    {w.runs.loading && <p role="status">Loading extraction history…</p>}
    {w.runs.error && <p role="alert" className="error">{w.runs.error}</p>}
    {w.runs.data?.length === 0 && <p>No extraction runs yet.</p>}
    {!!w.runs.data?.length && <label>Extraction run<select value={w.selectedRunId ?? ''} onChange={event => w.selectRun(event.target.value)}>
      {w.runs.data.map((run, index) => <option key={run.id} value={run.id}>{index === 0 ? 'Latest · ' : ''}{new Date(run.created_at).toLocaleString()} · {run.id.slice(0, 8)}</option>)}
    </select></label>}
    {w.extraction.loading && <p role="status">Loading extraction…</p>}
    {w.extraction.error && <div role="alert"><p className="error">{w.extraction.error}</p><button onClick={w.extraction.refresh}>Retry extraction</button></div>}
    {result && <>
      <p className={result.complete ? 'success' : 'warning'}>Extraction checklist: {result.complete ? 'all five fields found' : 'attention needed'}. This is a source-text assessment, not administrative approval.</p>
      <p className="muted">{result.extractor_version} · {result.checklist_version} · {new Date(result.created_at).toLocaleString()}</p>
      {w.sourcesChanged && <p className="warning" role="status">Documents changed since this extraction. Run extraction again to assess the current packet.</p>}
      {result.warnings.map((warning, index) => <p key={index} className="warning">{warning}</p>)}
      {fieldNames.map(field => <div className="field-result" key={field}>
        <div className="section-toolbar"><h3>{fieldLabels[field]}</h3><span className="badge">{result.findings.find(finding => finding.field === field)?.status ?? 'unknown'}</span></div>
        <p>Extracted value: <strong>{result.fields[field].value ?? 'No selected value'}</strong></p>
        {result.fields[field].candidates.map((candidate, index) => <div className="candidate" key={index}>
          <p>{candidate.raw_value || '(empty value)'}</p>
          {candidate.issue && <p className="error">{candidate.issue}</p>}
          {candidate.value !== null && candidate.issue === null && <button disabled={saving} onClick={() => onUse(field, candidate.value!)}>Use {fieldLabels[field].toLowerCase()}: {candidate.value} in correction</button>}
          <ul className="evidence-list">{candidate.evidence.map((evidence, evidenceIndex) => <li key={evidenceIndex}>
            <button className="text-button" onClick={() => w.openEvidence(evidence)}>
              View evidence: {w.documents.data?.find(doc => doc.id === evidence.document_id)?.original_filename ?? evidence.document_id}, page {evidence.page_number}
            </button><blockquote>{evidence.quote}</blockquote>
          </li>)}</ul>
        </div>)}
      </div>)}
    </>}
  </section>
}
