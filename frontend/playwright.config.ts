import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure' },
  webServer: [
    {
      command: '../backend/.venv/bin/python ../backend/tests/browser_server.py',
      env: { REFERRAL_TEST_GEMINI_MODE: process.env.REFERRAL_TEST_GEMINI_MODE || 'stub' },
      url: 'http://127.0.0.1:8001/api/health',
      reuseExistingServer: false,
      gracefulShutdown: { signal: 'SIGTERM', timeout: 5000 },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
})
