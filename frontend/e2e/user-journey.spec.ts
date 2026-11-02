import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('a new member can register, sign in, and reach their dashboard on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const username = `e2e_member_${Date.now()}`;
  const password = 'Nocturne!4827Pine';

  await page.goto('/register');
  await expect(page.getByRole('heading', { name: 'Join your community.' })).toBeVisible();
  const registerAccessibility = await new AxeBuilder({ page }).analyze();
  expect(registerAccessibility.violations).toEqual([]);
  await page.getByLabel('First name').fill('E2E');
  await page.getByLabel('Last name').fill('Member');
  await page.getByLabel('Email').fill(`${username}@example.test`);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByLabel('Confirm password').fill(password);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page).toHaveURL(/\/login\/?$/);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page).toHaveURL(/\/dashboard\/?$/);
  await expect(page.getByText('Welcome back', { exact: false })).toBeVisible();
});

test('the browse page has usable search and a mobile layout', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/browse');

  await expect(page.getByRole('heading', { name: 'The community board.' })).toBeVisible();
  const browseAccessibility = await new AxeBuilder({ page }).analyze();
  expect(browseAccessibility.violations).toEqual([]);
  await expect(page.getByRole('searchbox')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('searchbox').fill('blue bag');
  await page.getByRole('button', { name: 'Search' }).click();
  await expect(page).toHaveURL(/q=blue\+bag|q=blue%20bag/);
});
