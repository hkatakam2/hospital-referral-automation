import { expect, test } from '@playwright/test'

// A tiny, valid text PDF keeps the real upload/parser path in browser coverage.
function pdf(pages: (string[] | null)[]) {
  const objects: string[] = []
  const add = (value: string) => { objects.push(value); return objects.length }
  add('<< /Type /Catalog /Pages 2 0 R >>')
  add('')
  add('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
  const pageIds = pages.map(lines => {
    const content = lines ? 'BT /F1 12 Tf 72 720 Td ' + lines.map((line, i) =>
      `${i ? '0 -18 Td ' : ''}(${line.replace(/[\\()]/g, '\\$&')}) Tj`).join(' ') + ' ET' : ''
    const stream = add(`<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}\nendstream`)
    return add(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${stream} 0 R >>`)
  })
  objects[1] = `<< /Type /Pages /Kids [${pageIds.map(id => `${id} 0 R`).join(' ')}] /Count ${pageIds.length} >>`
  let body = '%PDF-1.4\n'
  const offsets = [0]
  objects.forEach((object, index) => { offsets.push(Buffer.byteLength(body)); body += `${index + 1} 0 obj\n${object}\nendobj\n` })
  const xref = Buffer.byteLength(body)
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n${offsets.slice(1).map(offset => `${String(offset).padStart(10, '0')} 00000 n \n`).join('')}trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`
  return Buffer.from(body)
}

const data = {
  patient_name: 'Avery Morgan', date_of_birth: '1974-03-12',
  referring_organization: 'Lakeside', requested_specialty: 'cardiology', referral_reason: 'Palpitations',
}
const complete = ['Patient: Avery Morgan', 'DOB: 1974-03-12', 'Referring Clinic: Lakeside', 'Specialty: cardiology', 'Reason: Palpitations']

test('real API: upload, extract, inspect evidence, correct, and recover history after reload', async ({ page, request }, testInfo) => {
  const created = await request.post('/api/referrals', { data })
  expect(created.status()).toBe(201)
  const referral = await created.json()
  await page.goto(`/referrals/${referral.id}`)
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'complete.pdf', mimeType: 'application/pdf', buffer: pdf([complete]) })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Uploaded complete.pdf.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByText('Extraction checklist: all five fields found', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'View evidence: complete.pdf, page 1' }).first().click()
  await expect(page.getByRole('heading', { name: 'Source: complete.pdf, page 1' })).toBeFocused()
  await expect(page.locator('.source-viewer blockquote')).toContainText('Patient: Avery Morgan')
  await page.screenshot({ path: testInfo.outputPath('review-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('review-mobile.png'), fullPage: true })
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.getByLabel('Patient name', { exact: true }).fill('Manual correction')
  await page.getByRole('button', { name: 'Use date of birth: 1974-03-12 in correction' }).click()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Manual correction')
  await page.getByRole('button', { name: 'Save corrections' }).click()
  await expect(page.getByText('Corrections saved.')).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Manual correction')
  await expect(page.getByText('Extraction checklist: all five fields found', { exact: false })).toBeVisible()
  // Adding contradictory evidence must not silently replace the historical run.
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'conflict.pdf', mimeType: 'application/pdf', buffer: pdf([['DOB: 1974-03-21']]) })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Documents changed since this extraction.', { exact: false })).toBeVisible()
  await page.reload()
  await expect(page.getByText('Documents changed since this extraction.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByText('conflicting', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Extraction run').locator('option')).toHaveCount(2)
  await page.getByRole('button', { name: 'Use date of birth: 1974-03-21 in correction' }).click()
  await expect(page.getByLabel('Date of birth', { exact: true })).toHaveValue('1974-03-21')
  // Copying is only a draft; the saved record still has its previous DOB.
  expect((await (await request.get(`/api/referrals/${referral.id}`)).json()).date_of_birth).toBe('1974-03-12')
  await page.getByRole('button', { name: 'Save corrections' }).click()
  await expect(page.getByText('Corrections saved.')).toBeVisible()
  await expect(page.getByText('conflicting', { exact: true })).toBeVisible()
  const options = await page.getByLabel('Extraction run').locator('option').evaluateAll(elements => elements.map(el => (el as HTMLOptionElement).value))
  await page.getByLabel('Extraction run').selectOption(options[1])
  await expect(page.getByText('Extraction checklist: all five fields found', { exact: false })).toBeVisible()
  await expect(page.getByText('Documents changed since this extraction.', { exact: false })).toBeVisible()
})

test('real API: rejects corrupt upload, retains missing findings, and displays partial page warnings', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  await page.goto(`/referrals/${referral.id}`)
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'bad.pdf', mimeType: 'application/pdf', buffer: Buffer.from('not a PDF') })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('PDF')
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'partial.pdf', mimeType: 'application/pdf', buffer: pdf([['Patient: Avery Morgan'], null]) })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Uploaded partial.pdf.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByText('missing', { exact: true })).toHaveCount(4)
  await expect(page.getByText('source coverage is incomplete', { exact: false })).toBeVisible()
  await page.getByLabel('Page', { exact: true }).selectOption('2')
  await expect(page.getByText('This page has no usable text.', { exact: false })).toBeVisible()
})

test('history errors do not block correction or document inspection', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  await page.route(`**/api/referrals/${referral.id}/extractions`, route => route.fulfill({ status: 503, json: { detail: 'History temporarily unavailable' } }))
  await page.goto(`/referrals/${referral.id}`)
  await expect(page.getByText('History temporarily unavailable')).toBeVisible()
  await page.getByLabel('Patient name', { exact: true }).fill('Still editable')
  await page.getByRole('button', { name: 'Save corrections' }).click()
  await expect(page.getByText('Corrections saved.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Source documents', exact: true })).toBeVisible()
  await page.unroute(`**/api/referrals/${referral.id}/extractions`)
  await page.getByRole('button', { name: 'Refresh history' }).click()
  await expect(page.getByText('No extraction runs yet.')).toBeVisible()
})
