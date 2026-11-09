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
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
  await expect(page.getByText('Policy: Demo referral intake · five-required-fields/2')).toBeVisible()
  await expect(page.getByText('Required by this policy', { exact: true })).toHaveCount(5)
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
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
  await expect(page.getByText('Policy: Demo referral intake · five-required-fields/2')).toBeVisible()
  await expect(page.getByText('Required by this policy', { exact: true })).toHaveCount(5)
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
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
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
    delete legacy.policy_assessment
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
  await expect(page.getByText('Policy definition was not recorded for this historical run.')).toBeVisible()
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
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
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
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toHaveCount(0)
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

test('Gemini workflow: production API and persistence with explicit stub or live provider', async ({ page, request }, testInfo) => {
  test.setTimeout(120_000)
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await page.goto(`/referrals/${referral.id}`)
  await expect(page.getByLabel('Extraction method')).toHaveValue('rules')
  const narrative = ['Avery Morgan, born 1974-03-12, was referred by Lakeside for cardiology.',
    'The reason for referral is Palpitations.']
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({
    name: 'narrative.pdf', mimeType: 'application/pdf', buffer: pdf([narrative]),
  })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Uploaded narrative.pdf.', { exact: false })).toBeVisible()
  await page.getByLabel('Extraction method').selectOption('gemini')
  await expect(page.getByText('Gemini sends this packet’s synthetic document text', { exact: false })).toBeVisible()
  // Keep unrelated draft edits through extraction and a failed subsequent run.
  await page.getByLabel('Patient name', { exact: true }).fill('Manual correction')
  const completed = page.waitForResponse(response => response.url().endsWith(`${base}/extractions`) && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  const response = await completed
  expect(response.status()).toBe(201)
  const saved = await response.json()
  expect(saved.extractor_version).toBe('gemini-claims/1')
  await testInfo.attach('saved-gemini-run', { contentType: 'application/json', body: JSON.stringify({
    providerMode: process.env.REFERRAL_TEST_GEMINI_MODE || 'stub', saved,
  }, null, 2) })
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
  await page.getByText('Run provenance', { exact: true }).click()
  await expect(page.getByText('Provider: gemini', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'View evidence: narrative.pdf, page 1' }).first().click()
  await expect(page.getByRole('heading', { name: 'Source: narrative.pdf, page 1' })).toBeFocused()
  await page.getByRole('button', { name: 'Use date of birth: 1974-03-12 in correction' }).click()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Manual correction')
  expect((await (await request.get(base)).json()).patient_name).toBe('Avery Morgan')

  // This failure is a frontend-only probe, separate from the provider/persistence run above.
  let failedWrites = 0
  await page.route(`**${base}/extractions`, route => {
    if (route.request().method() !== 'POST') return route.continue()
    failedWrites++
    return route.fulfill({ status: 504, json: { detail: 'Gemini request timed out; no retry' } })
  })
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByRole('alert').filter({ hasText: 'Gemini request timed out' })).toBeVisible()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Manual correction')
  await expect(page.getByText('Provider: gemini', { exact: true })).toBeVisible()
  expect(failedWrites).toBe(1)
  await page.unroute(`**${base}/extractions`)
  await page.getByRole('button', { name: 'Save corrections' }).click()
  await expect(page.getByText('Corrections saved.')).toBeVisible()
  await page.reload()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Manual correction')
  await expect(page.getByLabel('Extraction run')).toContainText('gemini-claims/1')
  expect(await (await request.get(`${base}/extractions/${saved.id}`)).json()).toEqual(saved)
  expect(await (await request.get(`${base}/extractions`)).json()).toHaveLength(1)
  await page.getByText('Run provenance', { exact: true }).click()
  await page.screenshot({ path: testInfo.outputPath('gemini-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('gemini-mobile.png'), fullPage: true })
})

test('mocked availability: Gemini disabled and discovery failure leave Rules usable', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  await page.route('**/api/extraction-methods', route => route.fulfill({ json: [
    { extractor: 'rules', available: true, reason: null },
    { extractor: 'gemini', available: false, reason: 'Gemini extraction is disabled on this server' },
  ] }))
  await page.goto(`/referrals/${referral.id}`)
  await expect(page.getByText('Gemini extraction is disabled on this server')).toBeVisible()
  await expect(page.getByLabel('Extraction method').locator('option[value="gemini"]')).toHaveJSProperty('disabled', true)
  await page.unroute('**/api/extraction-methods')
  await page.route('**/api/extraction-methods', route => route.fulfill({ status: 503 }))
  await page.reload()
  await expect(page.getByText('Could not check Gemini availability.', { exact: false })).toBeVisible()
  await expect(page.getByLabel('Extraction method')).toHaveValue('rules')
  await expect(page.getByLabel('Extraction method').locator('option[value="gemini"]')).toHaveJSProperty('disabled', true)
  await request.post(`/api/referrals/${referral.id}/documents`, { multipart: { file: {
    name: 'rules.pdf', mimeType: 'application/pdf', buffer: pdf([complete]),
  } } })
  await page.getByRole('button', { name: 'Refresh documents', exact: true }).click()
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
})


test('mocked detail: optional missing fields do not contradict a satisfied checklist', async ({ page, request }, testInfo) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await request.post(`${base}/documents`, { multipart: { file: {
    name: 'name-only.pdf', mimeType: 'application/pdf', buffer: pdf([['Patient: Avery Morgan']]),
  } } })
  const saved = await (await request.post(`${base}/extractions`)).json()
  await page.route(`**${base}/extractions/${saved.id}`, route => route.fulfill({ json: {
    ...saved, complete: true, checklist_version: 'demo-name-only/1',
    policy_assessment: {
      policy: { id: 'demo-name-only', version: '1', name: 'Demo name-only intake', required_fields: ['patient_name'] },
      requirements: [{ field: 'patient_name', satisfied: true, finding: 'found' }],
      source_coverage_satisfied: true,
    },
  } }))
  await page.goto(`/referrals/${referral.id}`)
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
  await expect(page.getByText('Required by this policy', { exact: true })).toHaveCount(1)
  await expect(page.getByText('Optional for this policy', { exact: true })).toHaveCount(4)
  await expect(page.getByText('missing', { exact: true })).toHaveCount(4)
  await expect(page.getByRole('button', { name: /^Use patient name:/ })).toBeVisible()
  await page.screenshot({ path: testInfo.outputPath('policy-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('policy-mobile.png'), fullPage: true })
  // This is only a rendering probe; the real stored result is still incomplete.
  expect((await (await request.get(`${base}/extractions/${saved.id}`)).json()).complete).toBe(false)
})

test('real workflow: request, attach more evidence, resume, and retain history across reload', async ({ page, request }, testInfo) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await page.goto(`/referrals/${referral.id}`)
  const workflow = page.getByRole('region', { name: 'Coordinator workflow' })
  await expect(workflow.getByText('Referral status: Received')).toBeVisible()
  await expect(workflow.getByText('No coordinator workflow actions recorded.')).toBeVisible()
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'initial.pdf', mimeType: 'application/pdf', buffer: pdf([complete]) })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Uploaded initial.pdf.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByText('Extraction checklist: configured checklist satisfied', { exact: false })).toBeVisible()
  const snapshot = await (await request.get(`${base}/extractions`)).json()
  const original = await (await request.get(`${base}/extractions/${snapshot[0].id}`)).json()
  await page.getByLabel('Patient name', { exact: true }).fill('Unsaved coordinator correction')
  await page.getByLabel('Reviewer name (demo identity)').fill('Demo coordinator')
  await page.getByLabel('Information needed', { exact: true }).fill('Confirmation of date of birth')
  await page.getByLabel('Reason for workflow action').fill('Coordinator requests supporting confirmation')
  await page.getByLabel('Include the selected result as request context').check()
  await page.getByRole('button', { name: 'Record missing-information request', exact: true }).click()
  await expect(workflow.getByText('Missing-information request recorded.')).toBeVisible()
  await expect(workflow.getByText('Referral status: Missing information')).toBeVisible()
  await expect(workflow.getByText('Missing information requested', { exact: true })).toBeVisible()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Unsaved coordinator correction')
  expect((await (await request.get(base)).json()).patient_name).toBe(data.patient_name)
  const firstHistory = await (await request.get(`${base}/review-events`)).json()
  expect(firstHistory).toHaveLength(1)
  expect(firstHistory[0].extraction_id).toBe(original.id)
  await page.screenshot({ path: testInfo.outputPath('workflow-desktop.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
  await page.screenshot({ path: testInfo.outputPath('workflow-mobile.png'), fullPage: true })
  await page.setViewportSize({ width: 1280, height: 720 })
  await page.reload()
  await expect(workflow.getByText('Referral status: Missing information')).toBeVisible()
  await expect(workflow.getByText('Information needed: Confirmation of date of birth')).toBeVisible()
  await page.getByLabel('Attach a synthetic PDF').setInputFiles({ name: 'confirmation.pdf', mimeType: 'application/pdf', buffer: pdf([['DOB: 1974-03-12']]) })
  await page.getByRole('button', { name: 'Upload PDF', exact: true }).click()
  await expect(page.getByText('Uploaded confirmation.pdf.', { exact: false })).toBeVisible()
  await page.getByRole('button', { name: 'Run extraction', exact: true }).click()
  await expect(page.getByLabel('Extraction run').locator('option')).toHaveCount(2)
  await expect(workflow.getByText('Referral status: Missing information')).toBeVisible()
  await page.getByLabel('Patient name', { exact: true }).fill('Saved coordinator correction')
  await page.getByRole('button', { name: 'Save corrections', exact: true }).click()
  await expect(page.getByText('Corrections saved.')).toBeVisible()
  await expect(workflow.getByText('Referral status: Missing information')).toBeVisible()
  await page.getByLabel('Reviewer name (demo identity)').fill('Second demo coordinator')
  await page.getByLabel('Reason for workflow action').fill('Additional information is ready for review')
  await page.getByRole('button', { name: 'Resume review', exact: true }).click()
  await expect(workflow.getByText('Review resumed.', { exact: true })).toBeVisible()
  await expect(workflow.getByText('Referral status: Review required')).toBeVisible()
  await expect(workflow.locator('ol > li')).toHaveCount(2)
  await page.reload()
  await expect(workflow.getByText('Referral status: Review required')).toBeVisible()
  await expect(workflow.locator('ol > li')).toHaveCount(2)
  const events = await (await request.get(`${base}/review-events`)).json()
  expect(events.map((event: { action: string }) => event.action)).toEqual(['resume_review', 'request_missing_information'])
  expect(events[1]).toEqual(firstHistory[0])
  expect(await (await request.get(`${base}/extractions/${original.id}`)).json()).toEqual(original)
  await page.getByRole('button', { name: 'View referenced extraction' }).click()
  await expect(page.getByLabel('Extraction run')).toHaveValue(original.id)
  await page.getByRole('link', { name: '← Referral inbox' }).click()
  await expect(page.locator('li').filter({ has: page.getByRole('link', { name: 'Saved coordinator correction', exact: true }) })).toContainText('Review required')
  await testInfo.attach('workflow-readback.json', { body: JSON.stringify({ referral: await (await request.get(base)).json(), events, original }), contentType: 'application/json' })
})

test('workflow conflict and failed history refresh preserve drafts without repeating writes', async ({ page, request }) => {
  const referral = await (await request.post('/api/referrals', { data })).json()
  const base = `/api/referrals/${referral.id}`
  await page.goto(`/referrals/${referral.id}`)
  const workflow = page.getByRole('region', { name: 'Coordinator workflow' })
  await expect(workflow.getByText('No coordinator workflow actions recorded.')).toBeVisible()
  await page.getByLabel('Patient name', { exact: true }).fill('Keep my unsaved correction')
  await page.getByLabel('Reviewer name (demo identity)').fill('Stale browser coordinator')
  await page.getByLabel('Information needed', { exact: true }).fill('More source information')
  await page.getByLabel('Reason for workflow action').fill('Please confirm details')
  // A second client advances the actual persisted workflow while this browser is stale.
  expect((await request.post(`${base}/information-requests`, { data: {
    reviewer: 'Other coordinator', reason: 'Needs confirmation', requested_information: 'Source confirmation', expected_workflow_version: 0,
  } })).status()).toBe(201)
  let writes = 0
  page.on('request', req => { if (req.method() === 'POST' && /information-requests|resume-review/.test(req.url())) writes++ })
  await page.getByRole('button', { name: 'Record missing-information request', exact: true }).click()
  await expect(workflow.getByRole('alert')).toContainText('Workflow changed')
  await expect(page.getByLabel('Information needed', { exact: true })).toHaveValue('More source information')
  await page.getByRole('button', { name: 'Refresh workflow', exact: true }).click()
  await expect(workflow.getByText('Referral status: Missing information')).toBeVisible()
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Keep my unsaved correction')
  // Mock only the subsequent history read, after a real successful resume transaction.
  await page.route(`**${base}/review-events`, route => route.fulfill({ status: 503, json: { detail: 'History temporarily unavailable' } }))
  await page.getByRole('button', { name: 'Resume review', exact: true }).click()
  await expect(workflow.getByText('Review resumed.', { exact: true })).toBeVisible()
  await expect(workflow.getByText('Referral status: Review required')).toBeVisible()
  await expect(workflow.getByRole('alert')).toContainText('History temporarily unavailable')
  expect(writes).toBe(2)
  await page.unroute(`**${base}/review-events`)
  await page.getByRole('button', { name: 'Refresh workflow', exact: true }).click()
  await expect(workflow.locator('ol > li')).toHaveCount(2)
  await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Keep my unsaved correction')
  expect(writes).toBe(2)
  expect((await (await request.get(`${base}/review-events`)).json())).toHaveLength(2)
})
