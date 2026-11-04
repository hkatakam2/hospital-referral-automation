export const fieldLabels = {
  patient_name: 'Patient name',
  date_of_birth: 'Date of birth',
  referring_organization: 'Referring organization',
  requested_specialty: 'Requested specialty',
  referral_reason: 'Referral reason',
} as const
export type FieldName = keyof typeof fieldLabels
export const fieldNames = Object.keys(fieldLabels) as FieldName[]
export type ReferralInput = Record<FieldName, string>
export const emptyReferral: ReferralInput = {
  patient_name: '', date_of_birth: '', referring_organization: '',
  requested_specialty: 'cardiology', referral_reason: '',
}
export interface Referral extends ReferralInput { id: string; created_at: string }
export interface DocumentSummary {
  id: string; referral_id: string; original_filename: string; sha256: string
  size_bytes: number; page_count: number; parse_status: 'parsed' | 'partial'
  parser_version: string; created_at: string
}
export interface DocumentPage { page_number: number; text: string; text_status: 'extracted' | 'no_text' }
export interface DocumentDetail extends DocumentSummary { pages: DocumentPage[] }
export interface Evidence { document_id: string; page_number: number; quote: string }
export interface Candidate { raw_value: string; value: string | null; issue: string | null; evidence: Evidence[] }
export interface ExtractionSummary {
  id: string; referral_id: string; created_at: string; extractor_version: string
  checklist_version: string; source_document_ids: string[]; complete: boolean
}
export interface ExtractionDetail extends ExtractionSummary {
  provenance?: {
    evidence_version: string; candidates_checked: number; candidates_rejected: number
    provider: string | null; model: string | null; model_version: string | null
    prompt_version: string | null; request_ms: number | null
  } | null
  fields: Record<FieldName, { value: string | null; candidates: Candidate[] }>
  findings: { field: FieldName; status: 'found' | 'missing' | 'conflicting' | 'invalid' }[]
  warnings: string[]
}

export type ExtractorChoice = 'rules' | 'gemini'
export interface ExtractionMethod {
  extractor: ExtractorChoice; available: boolean; reason: string | null
}
