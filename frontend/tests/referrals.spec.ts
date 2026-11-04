import { expect, test } from '@playwright/test'

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
