import { jsonBody, request } from './client'
import type { InformationRequest, Referral, ReviewEvent, WorkflowCommand } from './types'

export const listReviewEvents = (id: string, signal?: AbortSignal) =>
  request<ReviewEvent[]>(`/referrals/${id}/review-events`, { signal })
export const requestInformation = (id: string, data: InformationRequest) =>
  request<Referral>(`/referrals/${id}/information-requests`, { method: 'POST', ...jsonBody(data) })
export const resumeReview = (id: string, data: WorkflowCommand) =>
  request<Referral>(`/referrals/${id}/resume-review`, { method: 'POST', ...jsonBody(data) })
