import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("public landing and jobs have no synthetic workspace", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Your skills. Your potential. Your next chapter.",
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Explore jobs", exact: true }).click();
  await expect(page.locator("#jobs-count")).toContainText(
    "active opportunities",
  );
  await expect(page.locator("body")).not.toContainText("Alex Morgan");
  await page
    .getByLabel("Job title, company, or skill")
    .fill("no-such-role-unique");
  await page.getByRole("button", { name: "Find roles", exact: true }).click();
  await expect(page.locator("#job-results")).toContainText(
    "No matching opportunities yet.",
  );
  await page.screenshot({
    path: "../artifacts/stage4-jobs-empty.png",
    fullPage: true,
  });
  const axe = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa"])
    .analyze();
  expect(axe.violations.filter((v) => v.impact === "critical")).toEqual([]);
});
test("network failure displays retry and recovers", async ({ page }) => {
  await page.route("**/api/v1/jobs?**", (route) =>
    route.fulfill({ status: 503, json: { detail: "Temporarily unavailable" } }),
  );
  await page.goto("/#/jobs");
  await expect(page.locator("#job-results")).toContainText(
    "Temporarily unavailable",
  );
  await page.unroute("**/api/v1/jobs?**");
  await page.getByRole("button", { name: "Retry loading jobs" }).click();
  await expect(page.locator("#jobs-count")).toContainText(
    "active opportunities",
  );
});
test("mobile landing and sign-in retain page boundaries", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.goto("/#/login");
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});
