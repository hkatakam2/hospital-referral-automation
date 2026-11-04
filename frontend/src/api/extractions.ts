import { jsonBody, request } from './client'
import type { ExtractionDetail, ExtractionMethod, ExtractionSummary, ExtractorChoice } from './types'

export const listExtractions = (id: string, signal?: AbortSignal) =>
  request<ExtractionSummary[]>(`/referrals/${id}/extractions`, { signal })
export const getExtraction = (id: string, runId: string, signal?: AbortSignal) =>
  request<ExtractionDetail>(`/referrals/${id}/extractions/${runId}`, { signal })
export const listExtractionMethods = (signal?: AbortSignal) =>
  request<ExtractionMethod[]>('/extraction-methods', { signal })
export const createExtraction = (id: string, extractor: ExtractorChoice) =>
  request<ExtractionDetail>(`/referrals/${id}/extractions`, { method: 'POST', ...jsonBody({ extractor }) })
