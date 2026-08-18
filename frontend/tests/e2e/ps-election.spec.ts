import { expect, test } from '@playwright/test'

// Throwaway stack + EML fixtures (ws + ps): Playwright webServer (see playwright.config.ts).

test.describe('Provinciale Staten election (Drenthe PS fixture)', () => {
  test('homepage → provincie list → Drenthe CSB results → party matrix', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Provinciale Statenverkiezingen 2023' }).click()
    await expect(page).toHaveURL(/\/gsb\/?$/)
    await expect(page.getByRole('link', { name: 'Gemeente' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Provincies' })).toBeVisible()

    await page.getByRole('link', { name: 'Provincies' }).click()
    await expect(page).toHaveURL(/\/csb\/?$/)
    await expect(page.getByRole('link', { name: 'Drenthe' })).toBeVisible()

    await page.getByRole('link', { name: 'Drenthe' }).click()
    await expect(page).toHaveURL(/\/csb\/[^/]+\/resultaten\/?$/)
    await expect(page.getByRole('link', { name: 'Hele provincie' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Telresultaten' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'VVD' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'CDA' })).toBeVisible()

    await page.getByRole('link', { name: 'VVD' }).click()
    await expect(page).toHaveURL(/\/csb\/[^/]+\/resultaten\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { name: /Telresultaten lijst/ })).toBeVisible()
    await expect(page.getByRole('heading', { level: 3, name: 'VVD' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Kandidaat' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Totaal' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Aa en Hunze' })).toBeVisible()
  })
})
