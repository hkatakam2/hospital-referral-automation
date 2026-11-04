import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**/api/referrals/*/documents', route => route.fulfill({ json: [] }))
  await page.route('**/api/referrals/*/extractions', route => route.fulfill({ json: [] }))
})

const initial = {
  id: '00000000-0000-0000-0000-000000000001', patient_name: 'Avery Morgan',
  date_of_birth: '1974-03-12', referring_organization: 'Lakeside Primary Care',
  requested_specialty: 'cardiology', referral_reason: 'Palpitations',
  created_at: '2026-01-01T00:00:00Z',
}

test('create, correct only changed fields, and recover saved values on reload', async ({ page }) => {
  let saved = { ...initial }
  let exists = false
  let patch: unknown
  await page.route('**/api/referrals', async route => {
    if (route.request().method() === 'POST') {
      saved = { ...initial, ...route.request().postDataJSON() }; exists = true
      await route.fulfill({ status: 201, json: saved })
    } else await route.fulfill({ json: exists ? [saved] : [] })
  })
  await page.route(`**/api/referrals/${initial.id}`, async route => {
    if (route.request().method() === 'PATCH') {
      patch = route.request().postDataJSON(); saved = { ...saved, ...patch as object }
    }
    await route.fulfill({ json: saved })
  })
  await page.goto('/referrals')
  await expect(page.getByText('No referrals yet.', { exact: false })).toBeVisible()
  await page.getByLabel('Patient name', { exact: true }).fill(initial.patient_name)
  await page.getByLabel('Date of birth', { exact: true }).fill(initial.date_of_birth)
  await page.getByLabel('Referring organization', { exact: true }).fill(initial.referring_organization)
  await page.getByLabel('Referral reason', { exact: true }).fill(initial.referral_reason)
  await page.getByRole('button', { name: 'Create referral', exact: true }).click()
  await expect(page).toHaveURL(new RegExp(initial.id))
  await page.getByLabel('Patient name', { exact: true }).fill('Avery Corrected')
  await page.getByRole('button', { name: 'Save corrections' }).click()
  await expect(page.getByText('Corrections saved.')).toBeVisible()
  expect(patch).toEqual({ patient_name: 'Avery Corrected' })
  await page.reload()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Avery Corrected')
  await page.getByRole('link', { name: '← Referral inbox' }).click()
  await expect(page.getByRole('link', { name: 'Avery Corrected' })).toBeVisible()
})

test('failed correction preserves draft and renders field validation', async ({ page }) => {
  await page.route(`**/api/referrals/${initial.id}`, async route => {
    await route.fulfill(route.request().method() === 'PATCH' ? {
      status: 422, json: { detail: [{ loc: ['body', 'patient_name'], msg: 'Name rejected' }] },
    } : { json: initial })
  })
  await page.goto(`/referrals/${initial.id}`)
  await page.getByLabel('Patient name', { exact: true }).fill('Unsaved name')
  await page.getByRole('button', { name: 'Save corrections' }).click()
  await expect(page.getByText('Name rejected')).toBeVisible()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Unsaved name')
})

test('late referral responses cannot replace a newly selected referral', async ({ page }) => {
  const other = { ...initial, id: '00000000-0000-0000-0000-000000000002', patient_name: 'Jordan Lee' }
  let release = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route('**/api/referrals', route => route.fulfill({ json: [initial, other] }))
  await page.route(`**/api/referrals/${initial.id}`, async route => {
    await gate
    await route.fulfill({ json: initial }).catch(() => {})
  })
  await page.route(`**/api/referrals/${other.id}`, route => route.fulfill({ json: other }))
  await page.goto('/referrals')
  const firstRead = page.waitForRequest(`**/api/referrals/${initial.id}`)
  await page.getByRole('link', { name: initial.patient_name, exact: true }).click()
  await firstRead
  await page.getByRole('link', { name: '← Referral inbox' }).click()
  await page.getByRole('link', { name: other.patient_name, exact: true }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Jordan Lee')
  release()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Jordan Lee')
})

test('late source text cannot replace the currently selected document', async ({ page }) => {
  const document = { id: 'doc-a', referral_id: initial.id, original_filename: 'first.pdf', page_count: 1, parse_status: 'parsed' }
  const other = { ...document, id: 'doc-b', original_filename: 'second.pdf' }
  let release = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route(`**/api/referrals/${initial.id}`, route => route.fulfill({ json: initial }))
  await page.route(`**/api/referrals/${initial.id}/documents`, route => route.fulfill({ json: [document, other] }))
  await page.route(`**/api/referrals/${initial.id}/documents/doc-a`, async route => {
    await gate
    await route.fulfill({ json: { ...document, pages: [{ page_number: 1, text: 'OLD SOURCE', text_status: 'extracted' }] } }).catch(() => {})
  })
  await page.route(`**/api/referrals/${initial.id}/documents/doc-b`, route => route.fulfill({ json: { ...other, pages: [{ page_number: 1, text: 'CURRENT SOURCE', text_status: 'extracted' }] } }))
  await page.goto(`/referrals/${initial.id}`)
  const firstRead = page.waitForRequest('**/documents/doc-a')
  await page.getByRole('button', { name: 'first.pdf', exact: true }).click()
  await firstRead
  await page.getByRole('button', { name: 'second.pdf', exact: true }).click()
  await expect(page.locator('.source-viewer pre')).toHaveText('CURRENT SOURCE')
  release()
  await expect(page.getByText('OLD SOURCE', { exact: true })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'Source: second.pdf, page 1' })).toBeVisible()
})
