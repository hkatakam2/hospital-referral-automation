import { jsonBody, request } from './client'
import type { CorrectionCommand, CorrectionEvent, Referral, ReferralInput } from './types'

export const listReferrals = (signal?: AbortSignal) => request<Referral[]>('/referrals', { signal })
export const getReferral = (id: string, signal?: AbortSignal) => request<Referral>(`/referrals/${id}`, { signal })
export const createReferral = (data: ReferralInput) => request<Referral>('/referrals', { method: 'POST', ...jsonBody(data) })
export const updateReferral = (id: string, data: CorrectionCommand) =>
  request<Referral>(`/referrals/${id}`, { method: 'PATCH', ...jsonBody(data) })

export const listCorrectionEvents = (id: string, signal?: AbortSignal) =>
  request<CorrectionEvent[]>(`/referrals/${id}/correction-events`, { signal })
