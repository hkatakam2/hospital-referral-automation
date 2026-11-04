import { useCallback, useEffect, useRef, useState } from 'react'
import { errorMessage } from '../api/client'
import { getDocument, listDocuments, uploadDocument } from '../api/documents'
import { createExtraction, listExtractionMethods, getExtraction, listExtractions } from '../api/extractions'
import { getReferral } from '../api/referrals'
import type { ExtractorChoice, Evidence } from '../api/types'

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
  const methods = useResource(useCallback(signal => listExtractionMethods(signal), []))
  const [extractor, setExtractor] = useState<ExtractorChoice>('rules')
  const referral = useResource(useCallback(signal => getReferral(id, signal), [id]))
  const documents = useResource(useCallback(signal => listDocuments(id, signal), [id]))
  const runs = useResource(useCallback(signal => listExtractions(id, signal), [id]))
  const [selection, setSelection] = useState<{ documentId: string; page: number; quote?: string } | null>(null)
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const runId = selectedRunId ?? runs.data?.[0]?.id ?? null
  const extraction = useResource(useCallback(signal => runId ? getExtraction(id, runId, signal) : Promise.resolve(null), [id, runId]))
  const documentId = selection?.documentId ?? null
  const document = useResource(useCallback(signal => documentId ? getDocument(id, documentId, signal) : Promise.resolve(null), [id, documentId]))
  const upload = useWorkspaceWrite(async (file: File) => {
    const result = await uploadDocument(id, file)
    return { result, publish: () => {
      documents.refresh()
      setSelection({ documentId: result.id, page: 1 })
    } }
  }, 'refresh documents')
  const runExtraction = useWorkspaceWrite(async () => {
    const result = await createExtraction(id, extractor)
    return { result, publish: () => {
      setSelectedRunId(result.id)
      runs.refresh()
      documents.refresh()
    } }
  }, 'refresh history')
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
    methods, extractor, setExtractor, referral, documents, runs, extraction, document, selection, selectedDocument,
    selectedExtraction, selectedRunId: runId, selectRun: setSelectedRunId,
    selectDocument: (documentId: string) => setSelection({ documentId, page: 1 }),
    selectPage: (page: number) => {
      if (documentId) setSelection({ documentId, page })
    },
    openEvidence, sourcesChanged, upload, runExtraction,
  }
}
export type ReferralWorkspace = ReturnType<typeof useReferralWorkspace>

// Writes are explicit and never retried. Only an active workspace may publish their
// consequences; aborting a read cannot undo a write that the server has committed.
function useWorkspaceWrite<Args extends unknown[], T>(
  write: (...args: Args) => Promise<{ result: T; publish: () => void }>, recovery: string,
) {
  const active = useRef(false)
  const locked = useRef(false)
  const [state, setState] = useState<{ pending: boolean; error: string; data: T | null }>({
    pending: false, error: '', data: null,
  })
  useEffect(() => {
    active.current = true
    return () => { active.current = false }
  }, [])
  async function execute(...args: Args): Promise<T | null> {
    if (locked.current || !active.current) return null
    locked.current = true
    setState({ pending: true, error: '', data: null })
    try {
      const { result, publish } = await write(...args)
      if (!active.current) return null
      publish()
      setState({ pending: false, error: '', data: result })
      return result
    } catch (error) {
      if (active.current) setState({ pending: false, data: null,
        error: `${errorMessage(error)} If the connection was interrupted, ${recovery} before retrying.`,
      })
      return null
    } finally {
      locked.current = false
    }
  }
  return { ...state, execute }
}
