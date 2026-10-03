import { test, expect } from "@playwright/test";

test("smoke test: jobs filtering and country selector", async ({ page }) => {
  await page.goto("/#/jobs");
  await expect(page.locator("#job-search")).toBeVisible();

  // Country filter default is India
  const countrySelect = page.locator("select[name=country]");
  await expect(countrySelect).toHaveValue("India");

  // Experience level filter
  const expSelect = page.locator("select[name=experience_level]");
  await expect(expSelect).toBeVisible();
  await expSelect.selectOption("intern");

  // Remote and Salary Disclosed toggles
  const remoteCheckbox = page.locator("input[name=remote]");
  await expect(remoteCheckbox).toBeVisible();
  const salaryCheckbox = page.locator("input[name=salary_disclosed]");
  await expect(salaryCheckbox).toBeVisible();

  await page.getByRole("button", { name: "Find roles" }).click();
  await expect(page.locator("#jobs-count")).toBeVisible();
});

test("smoke test: candidate manual application and follow-up date", async ({
  page,
  request,
}) => {
  const suffix = Date.now();
  const password = "SmokePassword123!";
  const email = `candidate_smoke_${suffix}@example.com`;

  // Register
  await page.goto("/#/register");
  await page.getByLabel("Your name").fill("Smoke Tester");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create my account" }).click();

  // Navigate to tracker
  await page.goto("/#/applications");
  await expect(page.locator(".add-manual-btn")).toBeVisible();

  // Open manual application modal
  await page.locator(".add-manual-btn").click();
  await expect(page.locator("#manual-app-form")).toBeVisible();

  // Fill external application details
  await page.locator("#manual-app-form input[name=company]").fill("Razorpay");
  await page.locator("#manual-app-form input[name=title]").fill("Software Development Engineer");
  await page.locator("#manual-app-form input[name=url]").fill("https://razorpay.com/jobs/123");
  await page.locator("#manual-app-form button[type=submit]").click();

  // Card appears on kanban board
  await expect(page.locator(".kanban-card")).toContainText("Software Development Engineer");
  await expect(page.locator(".kanban-card")).toContainText("Razorpay");

  // Set follow-up reminder
  await page.locator(".set-followup").click();
  await expect(page.locator("#followup-form")).toBeVisible();
  await page.locator("#followup-form input[name=follow_up_at]").fill("2026-10-15");
  await page.locator("#followup-form button[type=submit]").click();

  await expect(page.locator(".kanban-card")).toContainText("Follow-up: 10/15/2026");
});
