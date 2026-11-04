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
  await page.getByText('Run provenance', { exact: true }).click()
  await expect(page.getByText('Source checks: 5 candidates checked; 0 rejected by shared checks.')).toBeVisible()
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
  await page.getByText('Run provenance', { exact: true }).click()
  await expect(page.getByText('Source checks: 5 candidates checked; 0 rejected by shared checks.')).toBeVisible()
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

test('mocked detail: shows Gemini provenance, rejection reasons, and legacy history', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await request.post(`${base}/documents`, { multipart: { file: {
    name: 'complete.pdf', mimeType: 'application/pdf', buffer: pdf([complete]),
  } } })
  const saved = await (await request.post(`${base}/extractions`)).json()
  const rejected = {
    ...saved, complete: false,
    provenance: { ...saved.provenance, candidates_rejected: 1, provider: 'gemini',
      model: 'test-model', model_version: 'test-revision', prompt_version: 'referral-claims/1' },
    fields: { ...saved.fields, patient_name: { value: null, candidates: [{
      raw_value: 'Invented Person', value: null, issue: 'Missing evidence', evidence: [],
    }] } },
    findings: saved.findings.map((finding: { field: string; status: string }) =>
      finding.field === 'patient_name' ? { ...finding, status: 'invalid' } : finding),
  }
  let historical = false
  await page.route(`**${base}/extractions/${saved.id}`, route => {
    if (!historical) return route.fulfill({ json: rejected })
    const legacy = { ...saved }
    delete legacy.provenance
    return route.fulfill({ json: legacy })
  })
  await page.goto(`/referrals/${referral.id}`)
  await expect(page.getByText('Cannot use this candidate: Missing evidence')).toBeVisible()
  await expect(page.getByText('No source citation supplied.')).toBeVisible()
  await expect(page.getByRole('button', { name: /^Use patient name:/ })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Use date of birth: 1974-03-12 in correction' })).toBeVisible()
  await page.getByText('Run provenance', { exact: true }).click()
  await expect(page.getByText('Source checks: 5 candidates checked; 1 rejected by shared checks.')).toBeVisible()
  await expect(page.getByText('Provider: gemini', { exact: true })).toBeVisible()
  await expect(page.getByText('Model: test-model', { exact: true })).toBeVisible()
  await expect(page.getByText('Model version: test-revision', { exact: true })).toBeVisible()
  await expect(page.getByText('Prompt version: referral-claims/1', { exact: true })).toBeVisible()
  historical = true
  await page.reload()
  await expect(page.getByText('Provenance was not recorded for this historical run.')).toBeVisible()
  await expect(page.getByText('Run provenance', { exact: true })).toHaveCount(0)
  expect(await (await request.get(`${base}/extractions/${saved.id}`)).json()).toEqual(saved)
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

test('a committed upload survives a failed list refresh without repeating the write', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  let writes = 0
  let failRefresh = true
  await page.route(`**/api/referrals/${referral.id}/documents`, route => {
    if (route.request().method() === 'POST') {
      writes++
      return route.continue()
    }
    return writes && failRefresh
      ? route.fulfill({ status: 503, json: { detail: 'Document list refresh failed' } })
      : route.continue()
  })
  await page.goto(`/referrals/${referral.id}`)
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'saved.pdf', mimeType: 'application/pdf', buffer: pdf([complete]) })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Uploaded saved.pdf.', { exact: false })).toBeVisible()
  await expect(page.getByText('Document list refresh failed')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Source: saved.pdf, page 1' })).toBeVisible()
  failRefresh = false
  await page.getByRole('button', { name: 'Refresh documents' }).click()
  await expect(page.getByRole('button', { name: 'saved.pdf', exact: true })).toBeVisible()
  expect(writes).toBe(1)
  expect(await (await request.get(`/api/referrals/${referral.id}/documents`)).json()).toHaveLength(1)
})

test('extraction retries are explicit and a failed history refresh does not repeat a committed run', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await request.post(`${base}/documents`, { multipart: { file: {
    name: 'complete.pdf', mimeType: 'application/pdf', buffer: pdf([complete]),
  } } })
  let writes = 0
  let failHistory = true
  await page.route(`**${base}/extractions`, route => {
    if (route.request().method() === 'POST') {
      writes++
      return writes === 1
        ? route.fulfill({ status: 503, json: { detail: 'Extraction unavailable' } })
        : route.continue()
    }
    return writes > 1 && failHistory
      ? route.fulfill({ status: 503, json: { detail: 'History refresh failed' } })
      : route.continue()
  })
  await page.goto(`/referrals/${referral.id}`)
  const run = page.getByRole('button', { name: 'Run extraction', exact: true })
  await run.click()
  await expect(page.getByRole('alert')).toContainText('Extraction unavailable')
  expect(writes).toBe(1)
  await run.click()
  await expect(page.getByText('Extraction checklist: all five fields found', { exact: false })).toBeVisible()
  await expect(page.getByText('History refresh failed')).toBeVisible()
  await expect(page.getByText('Extraction unavailable', { exact: false })).toHaveCount(0)
  failHistory = false
  await page.getByRole('button', { name: 'Refresh history' }).click()
  await expect(page.getByLabel('Extraction run').locator('option')).toHaveCount(1)
  expect(writes).toBe(2)
  expect(await (await request.get(`${base}/extractions`)).json()).toHaveLength(1)
})

test('late extraction reads cannot replace the selected run', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await request.post(`${base}/documents`, { multipart: { file: {
    name: 'original.pdf', mimeType: 'application/pdf', buffer: pdf([complete]),
  } } })
  const older = await (await request.post(`${base}/extractions`)).json()
  await request.post(`${base}/documents`, { multipart: { file: {
    name: 'conflict.pdf', mimeType: 'application/pdf', buffer: pdf([['DOB: 1974-03-21']]),
  } } })
  const latest = await (await request.post(`${base}/extractions`)).json()
  let release = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  await page.route(`**${base}/extractions/${older.id}`, async route => {
    await gate
    await route.fulfill({ json: older }).catch(() => {})
  })
  await page.goto(`/referrals/${referral.id}`)
  await expect(page.getByText('conflicting', { exact: true })).toBeVisible()
  const pending = page.waitForRequest(`**${base}/extractions/${older.id}`)
  await page.getByLabel('Extraction run').selectOption(older.id)
  await pending
  await page.getByLabel('Extraction run').selectOption(latest.id)
  await expect(page.getByText('conflicting', { exact: true })).toBeVisible()
  release()
  await expect(page.getByLabel('Extraction run')).toHaveValue(latest.id)
  await expect(page.getByText('Extraction checklist: all five fields found', { exact: false })).toHaveCount(0)
})

test('a write finishing after navigation cannot select a run in another workspace', async ({ page, request }) => {
  const first = await (await request.post('/api/referrals', { data })).json()
  const other = await (await request.post('/api/referrals', { data: { ...data, patient_name: 'Other workspace' } })).json()
  const base = `/api/referrals/${first.id}`
  await request.post(`${base}/documents`, { multipart: { file: {
    name: 'complete.pdf', mimeType: 'application/pdf', buffer: pdf([complete]),
  } } })
  let release = () => {}
  let committed = () => {}
  const gate = new Promise<void>(resolve => { release = resolve })
  const writeCommitted = new Promise<void>(resolve => { committed = resolve })
  await page.route(`**${base}/extractions`, async route => {
    if (route.request().method() !== 'POST') return route.continue()
    const response = await route.fetch()
    committed()
    await gate
    await route.fulfill({ response }).catch(() => {})
  })
  await page.goto(`/referrals/${first.id}`)
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await writeCommitted
  await page.getByRole('link', { name: '← Referral inbox' }).click()
  await page.getByRole('link', { name: 'Other workspace', exact: true }).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Other workspace')
  const completed = page.waitForResponse(response => response.url().endsWith(`${base}/extractions`) && response.request().method() === 'POST')
  release()
  await completed
  await expect(page.getByText('No extraction runs yet.')).toBeVisible()
  await expect(page.getByText('Extraction checklist:', { exact: false })).toHaveCount(0)
  expect(await (await request.get(`${base}/extractions`)).json()).toHaveLength(1)
  expect(await (await request.get(`/api/referrals/${other.id}/extractions`)).json()).toHaveLength(0)
})
