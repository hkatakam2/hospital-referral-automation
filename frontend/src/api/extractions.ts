import { request } from './client'
import type { ExtractionDetail, ExtractionSummary } from './types'

export const listExtractions = (id: string, signal?: AbortSignal) =>
  request<ExtractionSummary[]>(`/referrals/${id}/extractions`, { signal })
export const getExtraction = (id: string, runId: string, signal?: AbortSignal) =>
  request<ExtractionDetail>(`/referrals/${id}/extractions/${runId}`, { signal })
export const createExtraction = (id: string) =>
  request<ExtractionDetail>(`/referrals/${id}/extractions`, { method: 'POST' })
