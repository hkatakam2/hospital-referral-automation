import { jsonBody, request } from './client'
import type { Referral, ReferralInput } from './types'

export const listReferrals = (signal?: AbortSignal) => request<Referral[]>('/referrals', { signal })
export const getReferral = (id: string, signal?: AbortSignal) => request<Referral>(`/referrals/${id}`, { signal })
export const createReferral = (data: ReferralInput) => request<Referral>('/referrals', { method: 'POST', ...jsonBody(data) })
export const updateReferral = (id: string, data: Partial<ReferralInput>) =>
  request<Referral>(`/referrals/${id}`, { method: 'PATCH', ...jsonBody(data) })
