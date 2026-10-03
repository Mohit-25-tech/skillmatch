import { test, expect } from "@playwright/test";
import path from "node:path";
test("real candidate workflow: scores, save, tracker, notes, search, alerts, ATS and theme", async ({
  page,
  request,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const suffix = Date.now(),
    password = "browser-test-password-2026";
  const recruiter = await (
    await request.post("/api/v1/auth/register", {
      data: {
        name: "Browser Recruiter",
        email: `recruiter${suffix}@example.com`,
        password,
        role: "recruiter",
      },
    })
  ).json();
  const headers = { Authorization: `Bearer ${recruiter.access_token}` };
  const jobData = {
    title: `Python Engineer ${suffix}`,
    company: "Test Studio",
    location: "Remote",
    employment_type: "Full-time",
    description:
      "Build Python FastAPI PostgreSQL services with our collaborative engineering team. Required: Python. Nice to have: Docker.",
    skills: ["Python", "FastAPI", "PostgreSQL"],
    salary_min: null,
    salary_max: null,
  };
  const job = await (
    await request.post("/api/v1/jobs", { headers, data: jobData })
  ).json();
  await page.goto("/#/register");
  await page.getByLabel("Your name").fill("Browser Candidate");
  await page.getByLabel("Email address").fill(`candidate${suffix}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create my account" }).click();
  await expect(
    page.getByRole("heading", { name: "Your next move, Browser." }),
  ).toBeVisible();
  await page.getByRole("link", { name: "My resume", exact: true }).click();
  await page
    .locator("#resume-file")
    .setInputFiles(path.resolve("../artifacts/e2e-stage4-resume.docx"));
  await page.getByRole("button", { name: "Analyze my resume" }).click();
  await expect(page.locator(".resume-file")).toContainText(
    "e2e-stage4-resume.docx",
  );
  await page.goto(`/#/jobs/${job.id}`);
  await expect(page.locator(".big-gauge")).toBeVisible();
  await expect(page.locator(".job-salary")).toContainText("Not disclosed");
  await page.getByRole("button", { name: "Save role", exact: true }).click();
  await expect(page.locator("#toasts")).toContainText(
    "Saved in your application tracker",
  );
  await page.getByRole("link", { name: "Applications", exact: true }).click();
  await expect(page.locator(".kanban-card")).toContainText(jobData.title);
  await page
    .locator(".drag-handle")
    .dragTo(page.locator(".kanban-list[data-status=Applied]"));
  await expect(page.locator(".kanban-list[data-status=Applied]")).toContainText(
    jobData.title,
  );
  await page.locator(".tracker-status").selectOption("Interview");
  await expect(
    page
      .locator(".kanban-column")
      .filter({ has: page.getByRole("heading", { name: "Interview 1" }) }),
  ).toContainText(jobData.title);
  await page.getByRole("button", { name: "Notes & timeline" }).click();
  await page.getByLabel("Notes", { exact: true }).fill("Prepare API examples");
  await page.getByRole("button", { name: "Save notes", exact: true }).click();
  await page.getByRole("button", { name: "Notes & timeline" }).click();
  await expect(page.locator(".timeline")).toContainText("Prepare API examples");
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(
    page.locator(".stat-card").filter({ hasText: "Interviews" }),
  ).toContainText("1");
  await page.getByRole("link", { name: "Resume tools", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Resume readiness." }),
  ).toBeVisible();
  await expect(page.locator(".job-detail")).toContainText("text readiness");
  await page.goto("/#/jobs");
  await page.getByLabel("Job title, company, or skill").fill("Python");
  await page.getByRole("button", { name: "Find roles", exact: true }).click();
  await expect(page.locator(".job-card")).not.toHaveCount(0);
  await page.getByRole("button", { name: "Save this search" }).click();
  await page.getByLabel("Name", { exact: true }).fill("Python opportunities");
  await page.getByRole("button", { name: "Save search", exact: true }).click();
  const next = await request.post("/api/v1/jobs", {
    headers,
    data: { ...jobData, title: `Python Developer ${suffix}` },
  });
  expect(next.ok()).toBeTruthy();
  await expect(page.locator(".unread-count")).toHaveText("1", {
    timeout: 15000,
  });
  await page.getByRole("button", { name: "View notifications" }).click();
  await expect(page.locator(".notification-item")).toContainText(
    "Python Developer",
  );
  await page.getByRole("button", { name: "Mark as read" }).click();
  await expect(page.locator(".unread-count")).toBeHidden();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.keyboard.press("Control+k");
  await page.getByLabel("Jobs, companies, skills or pages").fill("Python");
  await expect(page.locator("#command-results")).toContainText(jobData.title);
  await page.keyboard.press("Escape");
  await page
    .getByRole("button", { name: "Toggle light or dark theme" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "../artifacts/stage4-mobile-light.png",
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("administrator sees real source controls and history", async ({
  page,
}) => {
  await page.goto("/#/login");
  await page.getByLabel("Email address").fill("admin@e2e.example");
  await page
    .getByLabel("Password", { exact: true })
    .fill("e2e-admin-test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await page.getByRole("link", { name: "Ingestion", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "test-disabled" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Configure", exact: true }).click();
  await page.getByLabel("Interval in minutes").fill("720");
  await page.getByRole("button", { name: "Save configuration" }).click();
  await page.getByRole("button", { name: "Run history" }).click();
  await expect(page.locator("dialog")).toContainText("No runs yet.");
});
