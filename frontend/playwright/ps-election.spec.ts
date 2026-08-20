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

  test('gemeente list → gemeente Aa en Hunze → party results', async ({ page }) => {
    await page.goto('/ps2023/gsb')
    await expect(page.getByRole('link', { name: 'Aa en Hunze' })).toBeVisible()

    await page.getByRole('link', { name: 'Aa en Hunze' }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { level: 1, name: 'Gemeente Aa en Hunze' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Resultaten per stembureau' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'Hele gemeente' })).toBeVisible()
    // "stembureau" or "stembureaus" depending on how many the fixture holds:
    // the heading is an ICU plural, so a single station reads "1 stembureau".
    await expect(page.getByRole('heading', { level: 2, name: /stembureaus? in Gemeente Aa en Hunze/ })).toBeVisible()
    await expect(page.getByRole('link', { name: /Gemeentehuis Gieten/ })).toBeVisible()

    await page.getByRole('link', { name: 'Hele gemeente' }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/resultaten\/?$/)
    await expect(page.getByRole('heading', { name: 'Telresultaten' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'VVD' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'CDA' })).toBeVisible()

    await page.getByRole('link', { name: 'VVD' }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/resultaten\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { level: 1, name: /Telresultaten gemeente/ })).toBeVisible()
    await expect(page.getByRole('heading', { name: /Telresultaten lijst/ })).toBeVisible()
    await expect(page.getByRole('heading', { level: 3, name: 'VVD' })).toBeVisible()
    await expect(page.getByText(/Meeuwissen-Dekker/)).toBeVisible()
    await expect(page.getByText(/Totaal stemmen lijst/)).toBeVisible()
  })

  test('stembureau list → stembureau results → party results', async ({ page }) => {
    await page.goto('/ps2023/gsb/1680-aa-en-hunze/csb/3-drenthe')
    await expect(page.getByRole('heading', { level: 1, name: 'Gemeente Aa en Hunze' })).toBeVisible()
    await expect(page.getByRole('link', { name: /Gemeentehuis Gieten/ })).toBeVisible()

    await page.getByRole('link', { name: /Gemeentehuis Gieten/ }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { level: 1, name: /Telresultaten stembureau/ })).toBeVisible()
    await expect(page.getByRole('heading', { level: 2, name: 'Telresultaten', exact: true })).toBeVisible()
    await expect(page.getByRole('link', { name: 'VVD' })).toBeVisible()
    await expect(page.getByRole('link', { name: 'CDA' })).toBeVisible()

    await page.getByRole('link', { name: 'VVD' }).click()
    await expect(page).toHaveURL(/\/gsb\/[^/]+\/csb\/[^/]+\/[^/]+\/[^/]+\/?$/)
    await expect(page.getByRole('heading', { name: /Telresultaten lijst/ })).toBeVisible()
    await expect(page.getByRole('heading', { level: 3, name: 'VVD' })).toBeVisible()
    await expect(page.getByText(/Meeuwissen-Dekker/)).toBeVisible()
    await expect(page.getByText(/Totaal stemmen lijst/)).toBeVisible()
  })
})
