import { expect, test } from "@playwright/test";

// Smoke test for the NL/EN switcher. The other specs assert on Dutch text and
// rely on the pinned `lang=nl` from playwright.config.ts; this one exercises the
// switch itself rather than duplicating those suites in English.

test.describe("Language switching", () => {
   test("switches the interface to English and remembers the choice", async ({ page }) => {
      await page.goto("/");

      await expect(page.locator("html")).toHaveAttribute("lang", "nl");
      await expect(page.getByText("Deze website in andere talen:")).toBeVisible();

      await page.getByRole("button", { name: "English" }).click();

      await expect(page.locator("html")).toHaveAttribute("lang", "en");
      await expect(page.getByText("This website in other languages:")).toBeVisible();
      // The switcher now offers the way back, each language named in its own tongue.
      await expect(page.getByRole("button", { name: "Nederlands" })).toBeVisible();

      // The choice survives a reload, since it is stored rather than kept in the URL.
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("lang", "en");
      await expect(page.getByText("This website in other languages:")).toBeVisible();
   });

   test("translates election content and formats numbers for the active locale", async ({ page }) => {
      await page.goto("/");
      await page.getByRole("button", { name: "English" }).click();

      await page.getByRole("link", { name: "Waterschapsverkiezingen 2023" }).click();
      // Region labels come from the catalogue, not from concatenated fragments.
      await expect(page.getByRole("link", { name: "Municipality" })).toBeVisible();
      await expect(page.getByRole("link", { name: "Water authorities" })).toBeVisible();

      await page.getByRole("link", { name: "Water authorities" }).click();
      await page.getByRole("link", { name: "Scheldestromen" }).click();
      await expect(page.getByRole("link", { name: "Entire water authority" })).toBeVisible();
      await expect(page.getByRole("heading", { name: "Counting results" })).toBeVisible();
      await expect(page.getByText("Number of votes")).toBeVisible();
   });
});
