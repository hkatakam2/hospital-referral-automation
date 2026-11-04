import { useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, errorMessage } from '../api/client'
import { fieldLabels, fieldNames } from '../api/types'
import type { FieldName, ReferralInput } from '../api/types'

export function ReferralForm({ value: draft, onChange, onSave, submitLabel = 'Create referral' }: {
  value: ReferralInput; onChange: (value: ReferralInput) => void
  onSave: (data: ReferralInput) => Promise<void>; submitLabel?: string
}) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [fields, setFields] = useState<Record<string, string>>({})
  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true); setError(''); setFields({})
    try { await onSave(draft) }
    catch (err) { setError(errorMessage(err)); if (err instanceof ApiError) setFields(err.fields) }
    finally { setPending(false) }
  }
  function change(field: FieldName, value: string) {
    onChange({ ...draft, [field]: value })
  }
  return <form onSubmit={submit}>
    <fieldset disabled={pending}>
      {fieldNames.map(field => <div className="form-field" key={field}>
        <label htmlFor={field}>{fieldLabels[field]}</label>
        {field === 'requested_specialty'
          ? <select id={field} value={draft[field]} onChange={e => change(field, e.target.value)}><option value="cardiology">Cardiology</option></select>
          : field === 'referral_reason'
            ? <textarea id={field} required value={draft[field]} onChange={e => change(field, e.target.value)} aria-invalid={!!fields[field]} aria-describedby={fields[field] ? `${field}-error` : undefined} />
            : <input id={field} required type={field === 'date_of_birth' ? 'date' : 'text'} value={draft[field]} onChange={e => change(field, e.target.value)} aria-invalid={!!fields[field]} aria-describedby={fields[field] ? `${field}-error` : undefined} />}
        {fields[field] && <span className="error" id={`${field}-error`}>{fields[field]}</span>}
      </div>)}
      {error && <p role="alert" className="error">{error}</p>}
      <button className="primary" type="submit">{pending ? 'Saving…' : submitLabel}</button>
    </fieldset>
  </form>
}
