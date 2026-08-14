import { expect, test } from '@playwright/test'

// Throwaway stack + WS fixtures: Playwright webServer (see playwright.config.ts).

test.describe('Waterschap election (Scheldestromen WS fixture)', () => {
  test('homepage → gemeente list → waterschappen → CSB results → party matrix', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Waterschapsverkiezingen 2023' }).click()
    await expect(page).toHaveURL(/\/gsb\/?$/)
    await expect(page.getByRole('link', { name: 'Gemeente' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Waterschappen' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Borsele' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Goes' })).toBeVisible()

    await page.getByRole('link', { name: 'Waterschappen' }).click()
    await expect(page).toHaveURL(/\/csb\/?$/)
    await expect(page.getByRole('link', { name: 'Scheldestromen' })).toBeVisible()

    await page.getByRole('link', { name: 'Scheldestromen' }).click()
    await expect(page).toHaveURL(/\/csb\/[^/]+\/resultaten\/?$/)
    await expect(page.getByRole('link', { name: 'Heel waterschap' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Telresultaten' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Partij voor Zeeland' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'CDA' })).toBeVisible()

    await page.getByRole('link', { name: 'Partij voor Zeeland' }).click()
    await expect(page).toHaveURL(/\/csb\/[^/]+\/resultaten\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { name: /Telresultaten lijst/ })).toBeVisible()
    await expect(page.getByRole('heading', { level: 3, name: 'Partij voor Zeeland' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Kandidaat' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Totaal' })).toBeVisible()
    await expect(page.getByRole('columnheader', { name: 'Borsele' })).toBeVisible()
  })

  test('homepage → gemeente list → gemeente Borsele', async ({ page }) => {
    await page.goto('/')

    await page.getByRole('link', { name: 'Waterschapsverkiezingen 2023' }).click()
    await expect(page).toHaveURL(/\/gsb\/?$/)
    await expect(page.getByRole('link', { name: 'Borsele' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Goes' })).toBeVisible()

    await page.getByRole('link', { name: 'Borsele' }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { level: 1, name: 'Gemeente Borsele' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Resultaten per stembureau' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Hele gemeente' })).toBeVisible()
    await expect(page.getByRole('heading', { level: 2, name: /stembureaus in Gemeente Borsele/ })).toBeVisible()
    await expect(page.getByRole('link', { name: /Heinkenszand/ })).toBeVisible()

    await page.getByRole('link', { name: 'Hele gemeente' }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/resultaten\/?$/)
    await expect(page.getByRole('heading', { name: 'Telresultaten' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Partij voor Zeeland' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'CDA' })).toBeVisible()
  })
})
