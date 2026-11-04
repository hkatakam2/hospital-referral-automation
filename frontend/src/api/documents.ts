import { request } from './client'
import type { DocumentDetail, DocumentSummary } from './types'

export const listDocuments = (id: string, signal?: AbortSignal) =>
  request<DocumentSummary[]>(`/referrals/${id}/documents`, { signal })
export const getDocument = (id: string, documentId: string, signal?: AbortSignal) =>
  request<DocumentDetail>(`/referrals/${id}/documents/${documentId}`, { signal })
export function uploadDocument(id: string, file: File) {
  const body = new FormData()
  body.append('file', file)
  return request<DocumentDetail>(`/referrals/${id}/documents`, { method: 'POST', body })
}
