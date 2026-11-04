import { useState } from 'react'
import type { FormEvent } from 'react'
import { errorMessage } from '../api/client'
import { uploadDocument } from '../api/documents'
import type { ReferralWorkspace } from '../hooks/useReferralWorkspace'
import { SourceTextViewer } from './SourceTextViewer'

export function DocumentPanel({ id, workspace: w }: { id: string; workspace: ReferralWorkspace }) {
  const [file, setFile] = useState<File | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!file || pending) return
    const form = event.currentTarget
    setPending(true); setError(''); setSuccess('')
    try {
      const result = await uploadDocument(id, file)
      w.documents.refresh()
      w.setSelection({ documentId: result.id, page: 1 })
      setSuccess(`Uploaded ${result.original_filename}. Run extraction to include this document.`)
      setFile(null); form.reset()
    } catch (err) { setError(`${errorMessage(err)} If the connection was interrupted, refresh documents before retrying.`) }
    finally { setPending(false) }
  }
  return <section className="card" aria-labelledby="documents-title">
    <h2 id="documents-title">Source documents</h2>
    <form onSubmit={upload}>
      <label>Attach a synthetic PDF<input type="file" accept="application/pdf,.pdf" required disabled={pending} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label>
      <button type="submit" disabled={pending || !file}>{pending ? 'Uploading and parsing…' : 'Upload PDF'}</button>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    {success && <p role="status" className="success">{success}</p>}
    <div className="section-toolbar"><h3>Attached documents</h3><button disabled={w.documents.loading} onClick={w.documents.refresh}>Refresh documents</button></div>
    {w.documents.loading && <p role="status">Loading documents…</p>}
    {w.documents.error && <p role="alert" className="error">{w.documents.error}</p>}
    {w.documents.data?.length === 0 && <p>No documents attached yet.</p>}
    <ul className="document-list">{w.documents.data?.map(doc => <li key={doc.id}>
      <button className="text-button" onClick={() => w.setSelection({ documentId: doc.id, page: 1 })}>{doc.original_filename}</button>
      <span className="muted">{doc.page_count} pages · {doc.parse_status === 'partial' ? 'Partial text — some pages have no usable text' : 'Text parsed'}</span>
    </li>)}</ul>
    {w.selection && <>
      {w.document.loading && <p role="status">Loading source text…</p>}
      {w.document.error && <div role="alert"><p className="error">{w.document.error}</p><button onClick={w.document.refresh}>Retry source text</button></div>}
      {w.selectedDocument && <SourceTextViewer document={w.selectedDocument} pageNumber={w.selection.page} quote={w.selection.quote}
        onPage={page => w.setSelection({ documentId: w.selectedDocument!.id, page })} />}
    </>}
  </section>
}
