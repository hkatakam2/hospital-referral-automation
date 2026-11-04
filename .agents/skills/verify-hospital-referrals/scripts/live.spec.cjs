// Run through verify.py; resolve the checkout's Playwright instead of installing another copy.
const { test, expect } = require(require('node:path').join(process.env.REFERRAL_VERIFY_REPO, 'frontend/node_modules/@playwright/test'));

test('real browser intake and correction persist through API reads and reload', async ({ page, request }, testInfo) => {
  await test.step('Create a synthetic referral through the inbox form', async () => {
    await page.goto('/referrals');
    await page.getByLabel('Patient name', { exact: true }).fill('Verification Avery Morgan');
    await page.getByLabel('Date of birth', { exact: true }).fill('1974-03-12');
    await page.getByLabel('Referring organization', { exact: true }).fill('Synthetic Lakeside Clinic');
    await page.getByLabel('Referral reason', { exact: true }).fill('Synthetic palpitations referral');
    await page.screenshot({ path: testInfo.outputPath('intake-before-submit.png'), fullPage: true });
    await page.getByRole('button', { name: 'Create referral', exact: true }).click();
    await expect(page).toHaveURL(/\/referrals\/[0-9a-f-]{36}$/);
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('Verification Avery Morgan');
  });
  const id = new URL(page.url()).pathname.split('/').pop();
  await test.step('Read the created record through the production API', async () => {
    const response = await request.get(`/api/referrals/${id}`);
    expect(response.status()).toBe(200);
    const created = await response.json();
    expect(created.patient_name).toBe('Verification Avery Morgan');
    await testInfo.attach('created-referral.json', { body: JSON.stringify(created, null, 2), contentType: 'application/json' });
  });
  await test.step('Save an explicit correction and read it back after reload', async () => {
    await page.getByLabel('Patient name', { exact: true }).fill('Verification Avery Corrected');
    await page.getByRole('button', { name: 'Save corrections', exact: true }).click();
    await expect(page.getByText('Corrections saved.', { exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel('Patient name', { exact: true })).toHaveValue('Verification Avery Corrected');
    const response = await request.get(`/api/referrals/${id}`);
    expect(response.status()).toBe(200);
    const corrected = await response.json();
    expect(corrected.patient_name).toBe('Verification Avery Corrected');
    expect(corrected.date_of_birth).toBe('1974-03-12');
    await testInfo.attach('corrected-referral.json', { body: JSON.stringify(corrected, null, 2), contentType: 'application/json' });
    await page.screenshot({ path: testInfo.outputPath('corrected-after-reload.png'), fullPage: true });
  });
  await test.step('Find the corrected referral in the inbox', async () => {
    await page.getByRole('link', { name: '← Referral inbox', exact: true }).click();
    await expect(page.getByRole('link', { name: 'Verification Avery Corrected', exact: true })).toBeVisible();
    await page.screenshot({ path: testInfo.outputPath('inbox-after-correction.png'), fullPage: true });
  });
});
