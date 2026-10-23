import { defineConfig, devices } from '@playwright/test';

const backendEnv = {
  DJANGO_DEBUG: 'True',
  DJANGO_SECRET_KEY: 'playwright-only-secret-not-used-in-production',
  DJANGO_ALLOWED_HOSTS: '127.0.0.1,localhost,testserver',
  DJANGO_CSRF_TRUSTED_ORIGINS: 'http://127.0.0.1:3300',
};
const pythonCommand = process.platform === 'win32' ? 'py' : 'python';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: 'http://127.0.0.1:3300',
    trace: 'retain-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: `${pythonCommand} manage.py runserver 127.0.0.1:8300 --noreload`,
      cwd: '../backend',
      url: 'http://127.0.0.1:8300/health/',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: backendEnv,
    },
    {
      command: 'npm run start -- --port 3300',
      url: 'http://127.0.0.1:3300',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        DJANGO_URL: 'http://127.0.0.1:8300',
        DJANGO_ENV: 'development',
        DJANGO_DEBUG: 'True',
        DJANGO_SECRET_KEY: backendEnv.DJANGO_SECRET_KEY,
        DJANGO_ALLOWED_HOSTS: backendEnv.DJANGO_ALLOWED_HOSTS,
      },
    },
  ],
});
