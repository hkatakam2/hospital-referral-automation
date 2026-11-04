import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '../api/client'
import { getDocument, listDocuments } from '../api/documents'
import { getExtraction, listExtractions } from '../api/extractions'
import { getReferral } from '../api/referrals'
import type { Evidence } from '../api/types'

// Each resource owns its error/loading state. A failed panel does not hide its siblings.
function useResource<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ data: T | null; loading: boolean; error: string }>({ data: null, loading: true, error: '' })
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(value => value + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    // Keep prior data while refreshing; never publish an obsolete response.
    const pending = Promise.resolve().then(() => {
      if (!controller.signal.aborted) setState(current => ({ ...current, loading: true, error: '' }))
      return load(controller.signal)
    })
    pending.then(data => {
      if (!controller.signal.aborted) setState({ data, loading: false, error: '' })
    }).catch(error => {
      if (!controller.signal.aborted) setState(current => ({ ...current, loading: false, error: errorMessage(error) }))
    })
    return () => controller.abort()
  }, [load, revision])
  return { ...state, refresh }
}

export function useReferralWorkspace(id: string) {
  const referral = useResource(useCallback(signal => getReferral(id, signal), [id]))
  const documents = useResource(useCallback(signal => listDocuments(id, signal), [id]))
  const runs = useResource(useCallback(signal => listExtractions(id, signal), [id]))
  const [selection, setSelection] = useState<{ documentId: string; page: number; quote?: string } | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const runId = selectedRunId ?? runs.data?.[0]?.id ?? null
  const extraction = useResource(useCallback(signal => runId ? getExtraction(id, runId, signal) : Promise.resolve(null), [id, runId]))
  const documentId = selection?.documentId ?? null
  const document = useResource(useCallback(signal => documentId ? getDocument(id, documentId, signal) : Promise.resolve(null), [id, documentId]))
  // Stale data may remain during a refresh, but must never render as another selection.
  const selectedDocument = document.data?.id === documentId ? document.data : null
  const selectedExtraction = extraction.data?.id === runId ? extraction.data : null
  function openEvidence(evidence: Evidence) {
    setSelection({ documentId: evidence.document_id, page: evidence.page_number, quote: evidence.quote })
  }
  const sourcesChanged = documents.data !== null && selectedExtraction !== null && (
    documents.data.length !== selectedExtraction.source_document_ids.length ||
    documents.data.some(doc => !selectedExtraction.source_document_ids.includes(doc.id))
  )
  return {
    referral, documents, runs, extraction, document, selection, selectedDocument,
    selectedExtraction, selectedRunId: runId, setSelectedRunId, setSelection, openEvidence, sourcesChanged,
  }
}
export type ReferralWorkspace = ReturnType<typeof useReferralWorkspace>
