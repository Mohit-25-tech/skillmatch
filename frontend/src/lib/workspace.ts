import $ from "jquery";
import Sortable from "sortablejs";
import { Chart, registerables } from "chart.js";
import { api, notificationStream } from "./api";
import { escapeHtml as e, salary, safeUrl, postedAge } from "./utils";
import type { User, Job, Match, Resume, Analytics } from "./types";
import type {
  Profile,
  Tracker,
  Notices,
  Learning,
  ATS,
  SavedSearch,
  Market,
  Source,
} from "./product-types";
Chart.register(...registerables);
type Context = {
  shell: (content: string, title?: string) => void;
  heading: (
    eyebrow: string,
    title: string,
    subtitle: string,
    action?: string,
  ) => string;
  jobCard: (job: Job) => string;
  toast: (message: string, type?: string) => void;
  user: () => User | null;
  navigate: () => Promise<void>;
  finish: () => void;
};
let ctx: Context;
let profile: Profile | null = null;
let learning: Learning[] = [];
let stopStream: (() => void) | undefined;
let chartList: Chart[] = [];
let sortables: Sortable[] = [];
let generation = 0;
let unread = 0;
let connection = "Connecting";
let trackerRows: Tracker[] = [];
const statuses = [
  "Saved",
  "Applied",
  "Reviewing",
  "Interview",
  "Offer",
  "Rejected",
  "Hired",
];
const empty = (message: string) =>
  `<div class="empty-state"><p>${e(message)}</p></div>`;
const anchor = (url: string, label: string) =>
  safeUrl(url)
    ? `<a class="text-link" href="${e(safeUrl(url))}" target="_blank" rel="noopener">${e(label)} ↗</a>`
    : e(label);
const date = (value: string) =>
  new Date(
    value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : value + "Z",
  ).toLocaleString();
const run = (action: () => Promise<void>) =>
  void action().catch((err) => ctx.toast(err.message, "error"));
const fields = (form: JQuery) =>
  Object.fromEntries(form.serializeArray().map((x) => [x.name, x.value]));
function draw(content: string, title: string, token: number) {
  if (token !== generation) return false;
  ctx.shell(content, title);
  updateBadge();
  return true;
}
export function stopWorkspace() {
  generation++;
  chartList.forEach((c) => c.destroy());
  chartList = [];
  sortables.forEach((s) => s.destroy());
  sortables = [];
  document
    .querySelectorAll("dialog.workspace-dialog")
    .forEach((d) => d.remove());
}
export function clearWorkspace() {
  stopStream?.();
  stopStream = undefined;
  profile = null;
  learning = [];
  unread = 0;
  connection = "Public jobs";
  stopWorkspace();
}
export function applyTheme() {
  const selected =
    profile?.preferences.theme || localStorage.getItem("sm-theme") || "dark";
  const theme =
    selected === "system"
      ? matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : selected;
  document.documentElement.dataset.theme = theme;
}
export async function loadPreferences() {
  profile = await api<Profile>("/profile");
  localStorage.setItem("sm-theme", profile.preferences.theme);
  applyTheme();
}
function updateBadge() {
  $(".unread-count")
    .text(unread)
    .prop("hidden", unread === 0);
  $(".connection-state").text(ctx.user() ? connection : "Public jobs");
}
export function startNotifications() {
  stopStream?.();
  stopStream = notificationStream(
    (data) => {
      unread = data.unread;
      updateBadge();
    },
    (state) => {
      connection = state;
      updateBadge();
    },
  );
}
export function learningItems() {
  return (
    learning
      .slice(0, 3)
      .map(
        (item) =>
          `<div class="learning-item"><span><strong>${e(item.skill)}</strong><small>${e(item.message || `Learning ${item.skill} unlocks ${item.related_jobs} more jobs`)}</small>${item.resources.map((r) => anchor(r.url, r.title)).join("<br>") || "<small>No curated resource yet</small>"}</span></div>`,
      )
      .join("") ||
    '<p class="subtle">Learning priorities appear after matching your resume.</p>'
  );
}
function modal(title: string, content: string) {
  $("dialog.workspace-dialog").remove();
  const dialog = $(
    `<dialog class="workspace-dialog"><div class="dialog-heading"><h2>${e(title)}</h2><button class="icon-btn close-dialog" aria-label="Close dialog">×</button></div>${content}</dialog>`,
  ).appendTo(document.body)[0] as HTMLDialogElement;
  dialog.showModal();
  return dialog;
}
function breakdown(match?: Match | null) {
  if (!match)
    return '<p class="subtle">Sign in and upload a resume for your match breakdown.</p>';
  return `<div class="big-gauge" style="--score:${match.score}"><span>${match.score}<small>%</small></span></div><p>${e(match.method)} match · A guide to fit, not a hiring decision.</p><dl class="score-breakdown">${Object.entries(
    match.components || {},
  )
    .map(
      ([key, value]) =>
        `<div><dt>${e(key)}</dt><dd>${value.score == null ? "Not available" : `${value.score}% · weight ${Math.round(value.weight * 100)}%`}</dd></div>`,
    )
    .join(
      "",
    )}</dl><h3>What you bring</h3><div class="strength-chips">${match.matched.map((s) => `<span class="skill-chip strength">${e(s)}</span>`).join("") || "No extracted skills matched."}</div><h3>Skills to develop</h3><div class="strength-chips">${match.missing.map((s) => `<span class="skill-chip missing">${e(s)}</span>`).join("") || "No skill gaps identified."}</div><ul>${(match.reasons || []).map((r) => `<li>${e(r)}</li>`).join("")}</ul><h3>How to improve</h3><ul>${(match.improvements || []).map((r) => `<li>${e(r)}</li>`).join("") || "<li>Keep your experience and evidence current.</li>"}</ul>`;
}
async function detail(id: number) {
  const token = generation;
  const job = await api<Job>(`/jobs/${id}`);
  if (
    !draw(
      `${ctx.heading(e(job.company), e(job.title), `${e(job.location)} · ${e(job.employment_type)} · ${e(postedAge(job.posted_at))}`)}<div class="job-detail-layout"><article class="panel job-detail"><h2>About the opportunity</h2><p class="job-salary">${e(salary(job.salary_min, job.salary_max, job.salary_currency, job.salary_interval))}</p><div class="source-links">${(job.sources || []).map((s) => anchor(s.url, s.name)).join(" · ") || e(job.source)}</div><div class="job-description">${e(job.description)}</div><div class="manage-actions">${ctx.user()?.role === "candidate" ? `<button class="btn btn-outline save-job" data-id="${id}">Save role</button>` : ""}${safeUrl(job.apply_url) ? anchor(job.apply_url!, "Apply on original site") : `<button class="btn btn-primary apply-job" data-id="${id}">Apply</button>`}${ctx.user()?.role === "candidate" && safeUrl(job.apply_url) ? `<button class="btn btn-outline apply-job" data-id="${id}">Record my application</button>` : ""}</div><p class="subtle">External applications must be completed on the original site.</p></article><aside class="panel fit-panel">${breakdown(job.match)}${ctx.user()?.role === "candidate" ? `<button class="btn btn-primary why-match-btn" data-id="${id}" style="margin-top:10px;width:100%;font-size:13px">✨ Why this match (AI Analysis)</button><button class="btn btn-outline tailor-job" data-id="${id}" style="margin-top:8px;width:100%;font-size:13px">📄 Tailor Resume & Cover Letter</button>` : ""}</aside></div><section class="section-title"><h2>Similar opportunities</h2></section><div id="similar-jobs" class="all-jobs-grid"><div class="skeleton"></div></div>`,
      "Job detail",
      token,
    )
  )
    return;
  try {
    const similar = await api<{ items: Job[]; method: string }>(
      `/jobs/${id}/similar`,
    );
    if (token === generation) {
      $("#similar-jobs").html(
        similar.items.map(ctx.jobCard).join("") ||
          empty("No similar active jobs yet."),
      );
      ctx.finish();
    }
  } catch (error) {
    if (token === generation)
      $("#similar-jobs").html(empty((error as Error).message));
  }
}
async function tracker() {
  const token = generation;
  let page = 1;
  const rows: Tracker[] = [];
  while (true) {
    const data = await api<{ items: Tracker[] }>(`/tracker?page=${page++}`);
    if (token !== generation) return;
    rows.push(...data.items);
    if (data.items.length < 50) break;
  }
  trackerRows = rows;
  const allStatuses = statuses;
  if (
    !draw(
      `${ctx.heading("EVERY NEXT STEP, TOGETHER.", "Your opportunities, in motion.", "Drag a card to update its status, or use its status selector.", '<div style="display:flex;gap:8px;align-items:center"><button class="btn btn-primary btn-sm add-manual-btn">+ Add application</button><a class="btn btn-outline btn-sm" href="/api/v1/tracker/export" download>Export CSV</a></div>')}<div class="kanban-board">${allStatuses
        .map(
          (status) =>
            `<section class="kanban-column"><h2>${status} <span>${rows.filter((r) => r.status === status).length}</span></h2><div class="kanban-list" data-status="${status}">${rows
              .filter((r) => r.status === status)
              .map(
                (row) =>
                  `<article class="kanban-card" data-id="${row.id}"><button class="drag-handle" aria-label="Drag ${e(row.job?.title || row.custom_title || "Application")}">⠿</button>${row.job?.id ? `<a href="#/jobs/${row.job.id}"><h3>${e(row.job.title)}</h3></a>` : `<h3>${e(row.custom_title || "Direct Application")}</h3>`}<p>${e(row.custom_company || row.job?.company || "External")}</p>${row.custom_url ? `<p style="margin:2px 0"><a href="${e(row.custom_url)}" target="_blank" rel="noopener" class="text-link" style="font-size:11px">Job URL ↗</a></p>` : ""}${row.follow_up_at ? `<div class="follow-up-badge" style="font-size:11px;color:#f59e0b;font-weight:600;margin:3px 0">📅 Follow-up: ${e(new Date(row.follow_up_at).toLocaleDateString())}</div>` : ""}<small>Updated ${e(date(row.updated_at))}</small><label>Status<select class="tracker-status" data-id="${row.id}">${allStatuses.map((s) => `<option ${s === row.status ? "selected" : ""}>${s}</option>`).join("")}</select></label><div style="display:flex;gap:8px;flex-wrap:wrap"><button class="text-link tracker-notes" data-id="${row.id}">Notes & timeline</button><button class="text-link set-followup" data-id="${row.id}" style="font-size:12px">Follow-up reminder</button>${row.status === "Saved" ? `<button class="text-link remove-saved" data-id="${row.id}">Remove saved job</button>` : ""}</div></article>`,
              )
              .join("")}</div></section>`,
        )
        .join(
          "",
        )}</div>${!rows.length ? empty("Save a job or add an external application to start your tracker.") : ""}`,
      "Applications",
      token,
    )
  )
    return;
  document.querySelectorAll<HTMLElement>(".kanban-list").forEach((el) =>
    sortables.push(
      Sortable.create(el, {
        group: "applications",
        handle: ".drag-handle",
        animation: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : 150,
        onEnd: (event) => {
          const id = Number(event.item.dataset.id),
            status = event.to.dataset.status!;
          if (status !== event.from.dataset.status) run(() => move(id, status));
        },
      }),
    ),
  );
}
async function move(id: number, status: string) {
  const row = trackerRows.find((r) => r.id === id);
  try {
    await api(`/tracker/${id}`, "PATCH", { status, notes: row?.notes || "" });
    ctx.toast("Application updated.");
  } finally {
    await tracker();
  }
}
async function settings() {
  const token = generation;
  await loadPreferences();
  const p = profile!.preferences;
  draw(
    `${ctx.heading("MAKE THIS SPACE YOURS.", "Your preferences. Your next chapter.", "Choose what matters to your next role.")}<form id="profile-form" class="panel job-form"><div class="row g-4">${[
      ["name", "Name", profile!.name],
      [
        "preferred_roles",
        "Preferred roles (comma-separated)",
        p.preferred_roles.join(", "),
      ],
      ["locations", "Locations (comma-separated)", p.locations.join(", ")],
      ["salary_expectation", "Expected salary", p.salary_expectation ?? ""],
      ["salary_currency", "Salary currency", p.salary_currency ?? ""],
    ]
      .map(
        ([key, label, value]) =>
          `<div class="col-md-6"><label for="pref-${key}">${label}</label><input id="pref-${key}" name="${key}" value="${e(value)}" ${key === "name" ? 'required minlength="2" maxlength="100"' : key === "salary_expectation" ? 'type="number" min="0"' : key === "salary_currency" ? 'pattern="[A-Z]{3}" maxlength="3"' : ""}></div>`,
      )
      .join("")}${[
      ["theme", "Theme", ["dark", "light", "system"]],
      ["remote_preference", "Work arrangement", ["any", "remote", "onsite"]],
      ["salary_interval", "Pay period", ["year", "month", "hour"]],
    ]
      .map(
        ([key, label, options]) =>
          `<div class="col-md-6"><label>${label}<select name="${key}">${(options as string[]).map((v) => `<option ${p[key as keyof typeof p] === v ? "selected" : ""}>${v}</option>`).join("")}</select></label></div>`,
      )
      .join("")}<div class="col-12">${[
      ["job_alerts", "In-app job alerts"],
      ["email_digest", "Optional daily email digest"],
      ["discoverable", "Allow recruiters to discover my name and match score"],
    ]
      .map(
        ([key, label]) =>
          `<label class="check-label"><input type="checkbox" name="${key}" ${p[key as keyof typeof p] ? "checked" : ""}>${label}</label>`,
      )
      .join(
        "",
      )}</div></div><p class="subtle">Resume content is not included in candidate rankings. Digest delivery requires a configured mail service.</p><p class="form-error" role="alert"></p><button class="btn btn-primary">Save preferences</button></form><section class="panel" style="margin-top:24px"><h2>Account & Privacy</h2><p class="subtle">Download your personal data archive (resumes, match scores, applications) or permanently delete your account.</p><div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px"><a class="btn btn-outline" href="/api/v1/auth/export" download>Export my personal data (JSON)</a><button class="btn btn-outline danger btn-delete-account">Permanently delete my account</button></div></section>`,
    "Settings",
    token,
  );
}
async function searches() {
  const token = generation;
  const rows = await api<SavedSearch[]>("/saved-searches");
  draw(
    `${ctx.heading("KEEP THE RIGHT DOORS OPEN.", "Saved searches & alerts.", "New matching roles can find you, too.")}<div class="all-jobs-grid">${rows.map((r) => `<article class="panel managed-job"><h2>${e(r.name)}</h2><p>${e(r.filters.keywords || "Any keywords")} · ${e(r.filters.location || "Any location")} · ${r.filters.min_match}% minimum</p><a class="text-link" href="#/jobs?${e(new URLSearchParams({ q: r.filters.keywords, location: r.filters.location, kind: r.filters.kind, min_match: String(r.filters.min_match) }).toString())}">View results</a><label class="check-label"><input class="search-alert-toggle" type="checkbox" data-id="${r.id}" ${r.alerts ? "checked" : ""}>Alerts enabled</label><button class="text-link delete-search" data-id="${r.id}">Delete search</button></article>`).join("") || empty("Save filters from Find jobs to create your first alert.")}<a class="panel course-card" href="#/jobs">Explore jobs and save a search ↗</a></div>`,
    "Saved searches",
    token,
  );
  $(".search-alert-toggle").on("change", function () {
    const row = rows.find((r) => r.id === Number($(this).data("id")))!;
    run(async () => {
      try {
        await api(`/saved-searches/${row.id}`, "PUT", {
          name: row.name,
          filters: row.filters,
          alerts: (this as HTMLInputElement).checked,
        });
      } catch (error) {
        await searches();
        throw error;
      }
    });
  });
}
async function learningPage() {
  const token = generation;
  await workspace.loadLearning();
  draw(
    `${ctx.heading("SMALL STEPS. NEW POSSIBILITIES.", "Your learning path.", "Priorities across all your matched roles, with curated free resources.")}<div class="all-jobs-grid">${learning.map((row) => `<article class="panel course-card"><h2>${e(row.skill)}</h2><p class="unlock-msg" style="color:var(--brand,#a78bfa);font-weight:600;font-size:13px;margin-bottom:8px">${e(row.message || `Learning ${row.skill} unlocks ${row.related_jobs} more jobs`)}</p><p class="subtle" style="font-size:12px">${row.related_jobs} related jobs</p>${row.resources.map((r) => `<p>${anchor(r.url, r.title)}<small>${e(r.provider)}</small></p>`).join("") || '<p class="subtle">No curated resource has been added for this skill yet.</p>'}</article>`).join("") || empty("Upload a resume and wait for matching to see learning priorities.")}</div>`,
    "Learning path",
    token,
  );
}
function atsHTML(report: ATS) {
  return `<h3>${report.score}% text readiness</h3><p>${e(report.method)}</p><p>${report.word_count} words · keyword coverage ${report.keyword_coverage == null ? "Not measured" : report.keyword_coverage + "%"}</p><ul>${Object.entries(
    { ...report.sections, ...report.checks },
  )
    .map(
      ([key, value]) =>
        `<li>${value ? "✓" : "Needs attention:"} ${e(key.replaceAll("_", " "))}</li>`,
    )
    .join("")}</ul>`;
}
async function resumeTools() {
  const token = generation;
  const rows = await api<Resume[]>("/resumes");
  if (!rows.length) {
    draw(
      empty('Upload a resume first. <a href="#/upload">Upload</a>'),
      "Resume tools",
      token,
    );
    return;
  }
  const report = await api<ATS>(`/resumes/${rows[0].id}/ats`);
  draw(
    `${ctx.heading("CLARITY FOR YOUR CAREER STORY.", "Resume readiness.", e(rows[0].filename))}<div class="panel job-detail">${atsHTML(report)}<a href="#/jobs" class="btn btn-primary">Choose a job for tailoring</a><a href="#/upload" class="btn btn-outline">Manage resume</a></div>`,
    "Resume tools",
    token,
  );
}
function plot(
  id: string,
  type: "bar" | "line",
  labels: string[],
  values: (number | null)[],
  label: string,
) {
  const canvas = document.getElementById(id) as HTMLCanvasElement | null;
  if (!canvas) return;
  chartList.push(
    new Chart(canvas, {
      type,
      data: {
        labels,
        datasets: [
          {
            label,
            data: values,
            backgroundColor: "#b59aff",
            borderColor: "#a485f7",
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: matchMedia("(prefers-reduced-motion: reduce)").matches
          ? false
          : { duration: 700 },
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    }),
  );
}
async function insights() {
  const token = generation;
  const data = await api<Market>("/insights/market");
  const own = ctx.user() ? await api<Analytics>("/analytics") : null;
  const charts = [
    ["companies", "Top hiring companies", data.companies],
    ["locations", "Jobs by location", data.locations],
    ["types", "Employment types", data.types],
    ["skills", "Skills in demand", data.skills],
  ] as const;
  if (
    !draw(
      `${ctx.heading("A CLEARER VIEW OF THE MARKET.", "Where opportunity is growing.", `${data.active_jobs} active non-demo jobs · Updated ${e(date(data.generated_at))}`)}${own ? `<div class="stats-grid"><div class="stat-card">Applications <strong>${own.applications}</strong></div><div class="stat-card">Interviews <strong>${own.interviews}</strong></div><div class="stat-card">Matched roles <strong>${own.matches}</strong></div><div class="stat-card">Average match <strong>${own.average_score}%</strong></div></div>` : ""}<div class="analytics-grid">${charts
        .map(
          ([id, title, counts]) =>
            `<section class="panel chart-panel"><h2>${title}</h2>${
              Object.keys(counts).length
                ? `<div class="chart-wrap"><canvas id="market-${id}" role="img" aria-label="${title}"></canvas></div><details><summary>View data</summary>${Object.entries(
                    counts,
                  )
                    .map(([key, value]) => `<p>${e(key)}: ${value}</p>`)
                    .join("")}</details>`
                : empty("No live observations yet.")
            }</section>`,
        )
        .join(
          "",
        )}<section class="panel chart-panel"><h2>Skill demand over time</h2><label>Skill<select id="trend-skill">${Object.keys(
        data.skills,
      )
        .map((s) => `<option>${e(s)}</option>`)
        .join(
          "",
        )}</select></label>${data.history.length ? '<div class="chart-wrap"><canvas id="market-trend" role="img" aria-label="Recorded skill demand over time"></canvas></div>' : empty("History begins with the first daily snapshot.")}<p class="subtle">Only recorded daily snapshots are shown.</p></section><section class="panel chart-panel"><h2>Published salary ranges</h2><label>Role and location<select id="salary-group"><option value="">Choose a comparable salary group</option>${data.salaries.map((s, i) => `<option value="${i}">${e(s.role)} · ${e(s.location)} · ${e(s.currency)}/${e(s.interval)}</option>`).join("")}</select></label><div id="salary-caption"></div><div class="chart-wrap"><canvas id="salary-chart" role="img" aria-label="Salary range midpoint distribution"></canvas></div>${!data.salaries.length ? empty("No disclosed salaries with known currency and pay period.") : ""}</section></div>`,
      "Insights",
      token,
    )
  )
    return;
  charts.forEach(([id, title, counts]) =>
    plot(
      "market-" + id,
      "bar",
      Object.keys(counts),
      Object.values(counts),
      title,
    ),
  );
  const trend = () => {
    Chart.getChart("market-trend")?.destroy();
    const skill = String($("#trend-skill").val() || "");
    plot(
      "market-trend",
      "line",
      data.history.map((h) => h.day),
      data.history.map((h) => h.skills[skill] ?? null),
      skill,
    );
  };
  $("#trend-skill").on("change", trend);
  if (data.history.length) trend();
  $("#salary-group").on("change", function () {
    Chart.getChart("salary-chart")?.destroy();
    if ($(this).val() === "") return;
    const group = data.salaries[Number($(this).val())];
    $("#salary-caption").text(
      `${group.count} disclosed ranges. Average midpoint: ${group.average.toLocaleString()} ${group.currency}/${group.interval}`,
    );
    plot(
      "salary-chart",
      "bar",
      group.values.map((_, i) => `Posting ${i + 1}`),
      group.values,
      `${group.currency}/${group.interval}`,
    );
  });
}
async function candidates(id: number) {
  const token = generation;
  const data = await api<{
    items: { candidate_id: number; name: string; score: number }[];
  }>(`/jobs/${id}/candidates`);
  draw(
    `${ctx.heading("PEOPLE BEHIND THE SKILLS.", "Ranked candidates.", "Names and match scores only. Use this as a starting point for human review.")}<div class="panel table-panel"><table class="app-table"><thead><tr><th>Candidate</th><th>Match</th></tr></thead><tbody>${data.items.map((r) => `<tr><td>${e(r.name)}</td><td>${r.score}%</td></tr>`).join("")}</tbody></table>${!data.items.length ? empty("No discoverable candidates have been matched to this job yet.") : ""}</div><a href="#/applications" class="text-link">Manage applicants</a>`,
    "Candidates",
    token,
  );
}
async function ingestion() {
  const token = generation;
  const data = await api<{ items: Source[]; worker_last_seen: string | null }>(
    "/admin/ingestion",
  );
  draw(
    `${ctx.heading("KEEP OPPORTUNITIES CURRENT.", "Ingestion sources.", `Worker last seen: ${data.worker_last_seen ? e(date(data.worker_last_seen)) : "No heartbeat yet"}`)}<p class="subtle">Configure sources you may republish. Public cards include source attribution and original links.</p><div class="all-jobs-grid">${data.items.map((s) => `<article class="panel managed-job"><h2>${e(s.key)}</h2><p>${e(s.kind)} · ${e(s.status)}</p><p>Last run: ${s.last_run_at ? e(date(s.last_run_at)) : "Never"}</p><p>Added ${s.stats.added ?? "—"} · Updated ${s.stats.updated ?? "—"} · Closed ${s.stats.closed ?? "—"}</p>${s.last_error ? `<p role="alert">${e(s.last_error)}</p>` : ""}<label class="check-label"><input type="checkbox" class="source-toggle" data-id="${s.id}" ${s.enabled ? "checked" : ""}>Enabled</label><button class="btn btn-outline source-run" data-id="${s.id}" ${!s.enabled ? "disabled" : ""}>Run now</button><button class="text-link source-config" data-id="${s.id}">Configure</button><button class="text-link source-history" data-id="${s.id}">Run history</button></article>`).join("") || empty("Start the worker to load source configuration.")}</div>`,
    "Ingestion",
    token,
  );
  $(".source-toggle").on("change", function () {
    run(async () => {
      try {
        await api(`/admin/ingestion/${$(this).data("id")}`, "PATCH", {
          enabled: (this as HTMLInputElement).checked,
        });
      } finally {
        await ingestion();
      }
    });
  });
  $(".source-config").on("click", function () {
    const s = data.items.find((s) => s.id === Number($(this).data("id")))!;
    modal(
      "Source configuration",
      `<form id="source-form" data-id="${s.id}" data-enabled="${s.enabled}"><label>Interval in minutes<input name="interval_minutes" type="number" min="60" required value="${s.interval_minutes}"></label><label>Adapter configuration (JSON)<textarea name="config" rows="8">${e(JSON.stringify(s.config, null, 2))}</textarea></label><p class="subtle">Credentials belong in environment variables.</p><button class="btn btn-primary">Save configuration</button></form>`,
    );
  });
}
export async function workspaceRoute(path: string) {
  if (path === "settings") await settings();
  else if (path === "learning") await learningPage();
  else if (path === "saved-searches") await searches();
  else if (path === "resume-tools") await resumeTools();
  else if (path === "ingestion") await ingestion();
  else if (/^candidates\/\d+$/.test(path))
    await candidates(Number(path.split("/")[1]));
  else return false;
  return true;
}
export const workspace = {
  updateBadge,
  init(context: Context) {
    ctx = context;
    bind();
  },
  detail,
  tracker,
  insights,
  async loadLearning() {
    learning = (await api<{ items: Learning[] }>("/learning-path")).items;
  },
};
function bind() {
  $(document).on("click", ".close-dialog", () => {
    $("dialog.workspace-dialog").remove();
  });
  $(document).on("click", ".theme-toggle", () =>
    run(async () => {
      if (!ctx.user()) {
        localStorage.setItem(
          "sm-theme",
          document.documentElement.dataset.theme === "dark" ? "light" : "dark",
        );
        applyTheme();
        return;
      }
      if (!profile) await loadPreferences();
      const updated = {
        ...profile!,
        preferences: {
          ...profile!.preferences,
          theme: (document.documentElement.dataset.theme === "dark"
            ? "light"
            : "dark") as "dark" | "light",
        },
      };
      profile = await api<Profile>("/profile", "PUT", updated);
      localStorage.setItem("sm-theme", profile.preferences.theme);
      applyTheme();
    }),
  );
  $(document).on("submit", "#profile-form", function (ev) {
    ev.preventDefault();
    const form = $(this),
      values = fields(form);
    run(async () => {
      const button = form.find("button").prop("disabled", true);
      try {
        profile = await api<Profile>("/profile", "PUT", {
          name: values.name,
          preferences: {
            theme: values.theme,
            preferred_roles: values.preferred_roles
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            locations: values.locations
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            remote_preference: values.remote_preference,
            salary_expectation: values.salary_expectation
              ? Number(values.salary_expectation)
              : null,
            salary_currency: values.salary_currency || null,
            salary_interval: values.salary_interval,
            ...Object.fromEntries(
              ["job_alerts", "email_digest", "discoverable"].map((k) => [
                k,
                form.find(`[name=${k}]`).is(":checked"),
              ]),
            ),
          },
        });
        applyTheme();
        ctx.toast("Preferences saved. Matches will refresh.");
      } catch (error) {
        form.find(".form-error").text((error as Error).message);
        throw error;
      } finally {
        button.prop("disabled", false);
      }
    });
  });
  $(document).on("change", ".tracker-status", function () {
    run(() => move(Number($(this).data("id")), String($(this).val())));
  });
  $(document).on("click", ".tracker-notes", function () {
    const row = trackerRows.find((r) => r.id === Number($(this).data("id")))!;
    modal(
      "Notes & timeline",
      `<form id="notes-form" data-id="${row.id}"><label>Notes<textarea name="notes" rows="5" maxlength="10000">${e(row.notes)}</textarea></label><button class="btn btn-primary">Save notes</button></form><ol class="timeline">${row.timeline.map((t) => `<li><strong>${e(t.status)}</strong> · ${e(date(t.created_at))}<p>${e(t.note)}</p></li>`).join("")}</ol>`,
    );
  });
  $(document).on("submit", "#notes-form", function (ev) {
    ev.preventDefault();
    const id = Number($(this).data("id")),
      row = trackerRows.find((r) => r.id === id)!;
    const notes = String($(this).find("textarea").val());
    run(async () => {
      const updated = await api<Tracker>(`/tracker/${id}`, "PATCH", {
        status: row.status,
        notes,
      });
      trackerRows = trackerRows.map((item) =>
        item.id === id ? updated : item,
      );
      $("dialog").remove();
      await tracker();
    });
  });
  $(document).on("click", ".add-manual-btn", () => {
    modal(
      "Add external application",
      `<form id="manual-app-form">
        <label>Company name<input name="company" required maxlength="150" placeholder="e.g. Razorpay, Postman, CRED"></label>
        <label>Role title<input name="title" required maxlength="150" placeholder="e.g. Software Engineer"></label>
        <label>Job URL (optional)<input name="url" type="url" placeholder="https://careers.example.com/..."></label>
        <label>Current status<select name="status">${statuses.map((s) => `<option value="${s}" ${s === "Applied" ? "selected" : ""}>${s}</option>`).join("")}</select></label>
        <label>Follow-up date (optional)<input name="follow_up_at" type="date"></label>
        <label>Notes (optional)<textarea name="notes" rows="3" placeholder="Notes, recruiter contacts, or referral details..."></textarea></label>
        <button class="btn btn-primary" type="submit">Add to tracker</button>
      </form>`,
    );
  });
  $(document).on("submit", "#manual-app-form", function (ev) {
    ev.preventDefault();
    const form = $(this);
    const val = fields(form);
    run(async () => {
      await api("/tracker/manual", "POST", {
        company: val.company,
        title: val.title,
        url: val.url || null,
        status: val.status,
        notes: val.notes || "",
        follow_up_at: val.follow_up_at ? new Date(val.follow_up_at).toISOString() : null,
      });
      $("dialog").remove();
      ctx.toast("Application added.");
      await tracker();
    });
  });
  $(document).on("click", ".set-followup", function () {
    const id = Number($(this).data("id"));
    const row = trackerRows.find((r) => r.id === id);
    if (!row) return;
    const curDate = row.follow_up_at ? row.follow_up_at.split("T")[0] : "";
    modal(
      "Follow-up reminder",
      `<form id="followup-form" data-id="${id}">
        <p>Set a follow-up reminder date for <strong>${e(row.custom_title || row.job?.title || "role")}</strong> at <strong>${e(row.custom_company || row.job?.company || "company")}</strong>.</p>
        <label>Reminder date<input name="follow_up_at" type="date" value="${curDate}"></label>
        <button class="btn btn-primary" type="submit">Save reminder</button>
      </form>`,
    );
  });
  $(document).on("submit", "#followup-form", function (ev) {
    ev.preventDefault();
    const id = Number($(this).data("id"));
    const row = trackerRows.find((r) => r.id === id);
    if (!row) return;
    const dateVal = $(this).find("[name=follow_up_at]").val();
    run(async () => {
      await api(`/tracker/${id}`, "PATCH", {
        status: row.status,
        notes: row.notes,
        follow_up_at: dateVal ? new Date(String(dateVal)).toISOString() : null,
      });
      $("dialog").remove();
      ctx.toast("Reminder saved.");
      await tracker();
    });
  });
  $(document).on("click", ".remove-saved", function () {
    run(async () => {
      await api(`/tracker/${$(this).data("id")}`, "DELETE");
      await tracker();
    });
  });
  $(document).on("click", ".delete-search", function () {
    run(async () => {
      await api(`/saved-searches/${$(this).data("id")}`, "DELETE");
      await searches();
    });
  });
  $(document).on("click", ".btn-delete-account", function () {
    if (
      confirm(
        "Are you sure you want to permanently delete your account and all associated resumes, applications, and search history? This cannot be undone.",
      )
    ) {
      run(async () => {
        await api("/auth/account", "DELETE");
        ctx.toast("Account permanently deleted.");
        localStorage.removeItem("sm-session");
        clearWorkspace();
        location.hash = "/register";
        location.reload();
      });
    }
  });
  $(document).on("click", ".save-search", () => {
    if (!ctx.user()) {
      location.hash = "/login";
      return;
    }
    modal(
      "Save this search",
      '<form id="save-search-form"><label>Name<input name="name" required maxlength="100" placeholder="My next role"></label><label class="check-label"><input type="checkbox" name="alerts" checked>Notify me about new matching jobs</label><button class="btn btn-primary">Save search</button></form>',
    );
  });
  $(document).on("submit", "#save-search-form", function (ev) {
    ev.preventDefault();
    const form = $(this),
      jobForm = $("#job-search");
    run(async () => {
      await api("/saved-searches", "POST", {
        name: form.find("[name=name]").val(),
        alerts: form.find("[name=alerts]").is(":checked"),
        filters: {
          keywords: String(jobForm.find("[name=q]").val() || ""),
          location: String(jobForm.find("[name=location]").val() || ""),
          kind: String(jobForm.find("[name=kind]").val() || ""),
          min_match: Number(jobForm.find("[name=min_match]").val() || 0),
        },
      });
      $("dialog").remove();
      ctx.toast("Search saved. Manage delivery in Settings.");
    });
  });
  $(document).on("click", ".notification-button", () =>
    run(async () => {
      if (!ctx.user()) {
        location.hash = "/login";
        return;
      }
      const data = await api<Notices>("/notifications");
      unread = data.unread;
      updateBadge();
      modal(
        "Notifications",
        `<div id="notification-list">${noticeHTML(data)}</div>${data.items.length === 100 ? `<button class="btn btn-outline more-notices" data-cursor="${data.next_cursor}">Load more</button>` : ""}`,
      );
    }),
  );
  $(document).on("click", ".more-notices", function () {
    const button = $(this);
    run(async () => {
      const data = await api<Notices>(
        `/notifications?after=${button.data("cursor")}`,
      );
      $("#notification-list").append(noticeHTML(data));
      button
        .data("cursor", data.next_cursor)
        .prop("hidden", data.items.length < 100);
    });
  });
  $(document).on("click", ".notice-read", function () {
    const button = $(this);
    run(async () => {
      await api(`/notifications/${button.data("id")}/read`, "POST");
      button.replaceWith("<small>Read</small>");
      const data = await api<Notices>("/notifications");
      unread = data.unread;
      updateBadge();
    });
  });
  $(document).on("click", ".why-match-btn", function () {
    const id = Number($(this).data("id"));
    const btn = $(this);
    btn.prop("disabled", true).text("Analyzing match with AI…");
    run(async () => {
      try {
        const data = await api<{
          narrative: string;
          match_score: number;
          matched_skills: string[];
          missing_skills: string[];
          provider: string;
        }>("/ai/why-match", "POST", { job_id: id });
        modal(
          "Why This Match — AI Fit Analysis",
          `<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
            <span class="badge" style="background:#10b981;color:#fff;padding:4px 10px;border-radius:12px;font-size:12px">100% Grounded in Verified Facts</span>
            <span style="font-size:12px;color:rgba(255,255,255,0.6)">Engine: ${e(data.provider)}</span>
          </div>
          <div class="narrative-content" style="white-space:pre-wrap;line-height:1.6;font-size:14px;background:rgba(255,255,255,0.03);padding:14px;border-radius:8px;border:1px solid rgba(255,255,255,0.08)">${e(data.narrative)}</div>
          <div style="margin-top:16px;text-align:right">
            <button class="btn btn-outline close-dialog">Close</button>
          </div>`,
        );
      } finally {
        btn.prop("disabled", false).text("✨ Why this match (AI Analysis)");
      }
    });
  });
  $(document).on("click", ".tailor-job", function () {
    const id = Number($(this).data("id"));
    const btn = $(this);
    btn.prop("disabled", true).text("Generating tailored resume & cover letter…");
    run(async () => {
      try {
        const [tailor, letter] = await Promise.all([
          api<{
            diff: string;
            actionable_tips: string[];
            grounding_rule: string;
          }>("/ai/tailor-resume", "POST", { job_id: id }),
          api<{
            cover_letter: string;
            job_title: string;
            company: string;
          }>("/ai/cover-letter", "POST", { job_id: id }),
        ]);

        const diffLines = tailor.diff
          .split("\n")
          .map((line) => {
            const color = line.startsWith("+")
              ? "#10b981"
              : line.startsWith("-")
                ? "#ef4444"
                : "rgba(255,255,255,0.7)";
            return `<div style="color:${color};font-family:monospace;font-size:12px;white-space:pre-wrap;">${e(line)}</div>`;
          })
          .join("");

        modal(
          "Resume Tailoring & Targeted Cover Letter",
          `<div style="display:flex;flex-direction:column;gap:16px">
            <div style="background:rgba(16,185,129,0.08);border-left:3px solid #10b981;border-radius:4px;padding:8px 12px;font-size:12px;color:#10b981">
              <strong>Grounding Guarantee:</strong> ${e(tailor.grounding_rule)}
            </div>
            <div>
              <h3 style="font-size:15px;margin-bottom:6px">Actionable Tailoring Tips</h3>
              <ul style="margin:0 0 0 18px;font-size:13px;line-height:1.5">${tailor.actionable_tips.map((t) => `<li>${e(t)}</li>`).join("")}</ul>
            </div>
            <div>
              <h3 style="font-size:15px;margin-bottom:6px">Targeted Resume Diff View</h3>
              <div style="background:#0f172a;padding:12px;border-radius:6px;max-height:220px;overflow-y:auto;border:1px solid rgba(255,255,255,0.1)">
                ${diffLines || "<small>No textual diffs required</small>"}
              </div>
            </div>
            <div>
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                <h3 style="font-size:15px;margin:0">Targeted Cover Letter</h3>
                <button class="btn btn-outline btn-sm copy-cover-letter" data-letter="${encodeURIComponent(letter.cover_letter)}" style="font-size:11px">Copy Cover Letter</button>
              </div>
              <textarea readonly style="width:100%;height:140px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.1);border-radius:6px;color:#fff;font-size:13px;padding:10px;resize:vertical;">${e(letter.cover_letter)}</textarea>
            </div>
          </div>`,
        );
      } finally {
        btn.prop("disabled", false).text("📄 Tailor Resume & Cover Letter");
      }
    });
  });
  $(document).on("click", ".copy-cover-letter", function () {
    const text = decodeURIComponent(String($(this).data("letter") || ""));
    navigator.clipboard.writeText(text);
    ctx.toast("Cover letter copied to clipboard!");
    $(this).text("Copied!");
  });
  $(document).on("click", ".source-run", function () {
    const button = $(this);
    button.prop("disabled", true);
    run(async () => {
      try {
        await api(`/admin/ingestion/${button.data("id")}/run`, "POST");
        ctx.toast("Ingestion queued. Refresh run history for progress.");
      } finally {
        button.prop("disabled", false);
      }
    });
  });
  $(document).on("click", ".source-history", function () {
    run(async () => {
      const data = await api<{
        items: {
          id: number;
          status: string;
          started_at: string;
          stats: Record<string, unknown>;
          error: string | null;
        }[];
      }>(`/admin/ingestion/${$(this).data("id")}/runs`);
      modal(
        "Recent ingestion runs",
        data.items
          .map(
            (r) =>
              `<article class="panel"><strong>${e(r.status)} · ${e(date(r.started_at))}</strong><pre>${e(JSON.stringify(r.stats, null, 2))}</pre><p>${e(r.error || "")}</p></article>`,
          )
          .join("") || empty("No runs yet."),
      );
    });
  });
  $(document).on("submit", "#source-form", function (ev) {
    ev.preventDefault();
    const form = $(this);
    run(async () => {
      await api(`/admin/ingestion/${form.data("id")}`, "PATCH", {
        enabled: form.data("enabled"),
        interval_minutes: Number(form.find("input").val()),
        config: JSON.parse(String(form.find("textarea").val())),
      });
      $("dialog").remove();
      await ingestion();
    });
  });
  $(document).on("click", ".top-search", function (ev) {
    ev.preventDefault();
    command();
  });
  $(document).on("keydown", (ev) => {
    if ((ev.ctrlKey || ev.metaKey) && ev.key?.toLowerCase() === "k") {
      ev.preventDefault();
      command();
    }
  });
  let timer: ReturnType<typeof setTimeout>;
  let requestNumber = 0;
  $(document).on("input", "#command-query", function () {
    clearTimeout(timer);
    const q = String($(this).val()),
      request = ++requestNumber;
    timer = setTimeout(
      () =>
        run(async () => {
          if (!q.trim()) {
            $("#command-results").empty();
            return;
          }
          $("#command-results").html(
            '<div class="skeleton" aria-label="Searching"></div>',
          );
          try {
            const data = await api<{
              jobs: Job[];
              companies: string[];
              skills: string[];
              pages: { label: string; path: string }[];
            }>(`/search?q=${encodeURIComponent(q)}`);
            if (request !== requestNumber) return;
            $("#command-results").html(
              [
                ...data.jobs.map(
                  (j) =>
                    `<a href="#/jobs/${j.id}">${e(j.title)} <small>${e(j.company)}</small></a>`,
                ),
                ...data.companies.map(
                  (c) =>
                    `<a href="#/jobs?q=${encodeURIComponent(c)}">Company: ${e(c)}</a>`,
                ),
                ...data.skills.map(
                  (c) =>
                    `<a href="#/jobs?q=${encodeURIComponent(c)}">Skill: ${e(c)}</a>`,
                ),
                ...data.pages.map(
                  (p) => `<a href="#${e(p.path)}">${e(p.label)}</a>`,
                ),
              ].join("") || empty("No results found."),
            );
          } catch (error) {
            if (request === requestNumber)
              $("#command-results").html(empty((error as Error).message));
          }
        }),
      250,
    );
  });
  $(document).on("keydown", "#command-query", (ev) => {
    if (ev.key === "ArrowDown") {
      ev.preventDefault();
      $("#command-results a").first().trigger("focus");
    }
    if (ev.key === "Enter") {
      ev.preventDefault();
      const first = $("#command-results a").first().attr("href");
      if (first) location.hash = first;
    }
  });
  $(document).on("click", "#command-results a", () => {
    $("dialog").remove();
  });
  void api<{ ollama_enabled: boolean }>("/capabilities")
    .then((data) => (capabilities = data))
    .catch(() => {});
}
let capabilities = { ollama_enabled: false };
function command() {
  modal(
    "Search your workspace",
    '<label for="command-query">Jobs, companies, skills or pages</label><input id="command-query" autocomplete="off" maxlength="100" placeholder="What is your next move?"><div id="command-results" aria-live="polite"></div>',
  );
  $("#command-query").trigger("focus");
}
function noticeHTML(data: Notices) {
  return (
    data.items
      .map(
        (n) =>
          `<article class="notification-item"><a href="#/jobs/${n.job_id}">${e(n.title)}</a><small>${e(date(n.created_at))}</small>${n.read ? "<small>Read</small>" : `<button class="text-link notice-read" data-id="${n.id}">Mark as read</button>`}</article>`,
      )
      .join("") || empty("No notifications yet. Save a search to get started.")
  );
}
