import $ from "jquery";
import "bootstrap/dist/css/bootstrap.min.css";
import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-700.css";
import "@fontsource/manrope/latin-800.css";
import "@fontsource/dm-sans/latin-400.css";
import "@fontsource/dm-sans/latin-500.css";
import "@fontsource/dm-sans/latin-600.css";
import {
  createIcons,
  Zap,
  Sparkles,
  LayoutDashboard,
  FileUser,
  SquarePlus,
  BriefcaseBusiness,
  ScanLine,
  Layers,
  ChartNoAxesCombined,
  Shield,
  CircleHelp,
  ArrowUpRight,
  LogIn,
  LogOut,
  Menu,
  ChevronRight,
  Search,
  Bell,
  X,
  CircleAlert,
  CircleCheck,
  Upload,
  ArrowRight,
  Atom,
  Figma,
  Code2,
  Clock3,
  MapPin,
  Bookmark,
  TrendingUp,
  Target,
  Send,
  MessagesSquare,
  Lightbulb,
  FileText,
  FilePenLine,
  Network,
  Triangle,
  CloudUpload,
  ShieldCheck,
  FileScan,
  Route,
  Trash2,
  ArrowLeft,
  Banknote,
  Sprout,
  BookOpen,
  Plus,
  Pencil,
  Eye,
  FileCheck,
  ArrowDown,
  Users,
} from "lucide";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import "./styles/main.css";
import "./styles/workspace.css";
import "./styles/assistant.css";
import { api, refreshSession, setToken, aiChatStream } from "./lib/api";
import {
  workspace,
  workspaceRoute,
  loadPreferences,
  startNotifications,
  stopWorkspace,
  applyTheme,
  learningItems,
  clearWorkspace,
} from "./lib/workspace";
import {
  escapeHtml as e,
  initials,
  salary,
  scoreLabel,
  validateFile,
  safeUrl,
  postedAge,
} from "./lib/utils";
import type {
  Analytics,
  Application,
  CandidateProfile,
  Job,
  Match,
  Resume,
  User,
} from "./lib/types";

const icons = {
  Zap,
  Sparkles,
  LayoutDashboard,
  FileUser,
  SquarePlus,
  BriefcaseBusiness,
  ScanLine,
  Layers,
  ChartNoAxesCombined,
  Shield,
  Users,
  CircleHelp,
  ArrowUpRight,
  LogIn,
  LogOut,
  Menu,
  ChevronRight,
  Search,
  Bell,
  X,
  CircleAlert,
  CircleCheck,
  Upload,
  ArrowRight,
  Atom,
  Figma,
  Code2,
  Clock3,
  MapPin,
  Bookmark,
  TrendingUp,
  Target,
  Send,
  MessagesSquare,
  Lightbulb,
  FileText,
  FilePenLine,
  Network,
  Triangle,
  CloudUpload,
  ShieldCheck,
  FileScan,
  Route,
  Trash2,
  ArrowLeft,
  Banknote,
  Sprout,
  BookOpen,
  Plus,
  Pencil,
  Eye,
  FileCheck,
  ArrowDown,
};
gsap.registerPlugin(ScrollTrigger);
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let user: User | null = null;

let jobs: Job[] = [];
let resumes: Resume[] = [];
let matches: Match[] = [];
let analytics: Analytics;
let cleanupScene: (() => void) | undefined;
let cleanupCharts: (() => void) | undefined;
let renderId = 0;
let selectedFile: File | null = null;
const icon = (name: string, cls = "") =>
  `<i data-lucide="${name}" class="${cls}" aria-hidden="true"></i>`;
const link = (path: string, label: string, iconName: string) =>
  `<a href="#/${path}" class="nav-item ${route().split("/")[0] === path ? "active" : ""}">${icon(iconName)}<span>${label}</span>${path === "jobs" ? '<span class="nav-count">' + "Explore" + "</span>" : ""}</a>`;
function route(): string {
  return location.hash.replace(/^#\/?/, "") || (user ? "dashboard" : "landing");
}
function toast(message: string, type = "success"): void {
  const t = $(
    `<div class="app-toast ${type}" role="status">${icon(type === "error" ? "circle-alert" : "circle-check")}<span>${e(message)}</span><button aria-label="Dismiss notification">${icon("x")}</button></div>`,
  );
  $("#toasts").append(t);
  t.find("button").on("click", () => t.remove());
  createIcons({ icons });
  setTimeout(() => t.remove(), 6000);
}
function logo(): string {
  return `<a class="brand" href="#/dashboard" aria-label="SkillMatch AI dashboard"><span class="brand-symbol">${icon("zap")}</span><span>skillmatch<span class="brand-ai">AI</span></span></a>`;
}
function shell(content: string, title = "Overview"): void {
  const name = user?.name || "Guest";
  const recruiter = user?.role === "recruiter";
  $("#app").html(
    `<aside class="sidebar">${logo()}<div class="workspace-label">${recruiter ? "RECRUITER WORKSPACE" : "YOUR WORKSPACE"}</div><nav aria-label="Main navigation">${link(recruiter ? "recruiter" : "dashboard", "Overview", "layout-dashboard")}${!recruiter ? link("upload", "My resume", "file-user") : link("post-job", "Post a job", "square-plus")}${!recruiter ? link("jobs", "Find jobs", "briefcase-business") : ""}${user?.role === "candidate" ? link("assistant", "Career Assistant", "sparkles") + link("resume-tools", "Resume tools", "file-scan") + link("matches", "My matches", "scan-line") : ""}${link(recruiter ? "candidates" : "applications", recruiter ? "Candidates" : "Applications", recruiter ? "users" : "layers")}${link("analytics", "Insights", "chart-no-axes-combined")}${user?.role === "candidate" ? link("learning", "Learning path", "book-open") + link("saved-searches", "Saved searches", "bell") : ""}${user && user?.role === "candidate" ? link("settings", "Settings", "pencil") : ""}${user?.role === "admin" ? link("ingestion", "Ingestion", "cloud-upload") : ""}${user?.role === "admin" ? link("admin", "Administration", "shield") : ""}</nav><div class="sidebar-bottom">${recruiter ? `<div class="career-card"><span class="tiny-spark">${icon("sparkles")}</span><strong>Build your dream team.<br>Find the right fit.</strong><p>Verified skills & AI candidate ranking.</p><a href="#/post-job">Post a new role ${icon("arrow-up-right")}</a></div>` : `<div class="career-card"><span class="tiny-spark">${icon("sparkles")}</span><strong>Your next chapter<br>starts with you.</strong><p>A little clarity. A big step forward.</p><a href="#/upload">Find your potential ${icon("arrow-up-right")}</a></div>`}<a href="#/landing" class="help-link">${icon("circle-help")} How SkillMatch works ${icon("arrow-up-right")}</a><div class="sidebar-profile"><div class="avatar">${e(initials(name))}</div><div><strong>${e(name)}</strong><span>${e(user?.role ? (recruiter ? "Recruiter / Hiring" : "Job seeker") : "Public job browser")}</span></div><button class="icon-btn" id="account-button" aria-label="${!user ? "Sign in" : "Sign out"}">${icon(!user ? "log-in" : "log-out")}</button></div></div></aside><div class="sidebar-scrim"></div><div class="app-layout"><header class="topbar"><div class="topbar-title"><button class="icon-btn menu-toggle" aria-label="Open navigation">${icon("menu")}</button><span class="breadcrumb-home">${recruiter ? "Hiring" : "Workspace"}</span>${icon("chevron-right")}<strong>${e(title)}</strong></div><div class="topbar-actions"><a class="top-search" href="${recruiter ? "#/candidates" : "#/jobs"}">${icon("search")}<span>${recruiter ? "Search candidates & talent pool" : "Search your next opportunity"}</span><kbd>Ctrl K</kbd></a><span class="demo-badge connection-state">${user ? "Connected" : "Public jobs"}<span></span></span>${!recruiter ? `<button class="btn btn-outline btn-sm ai-assistant-btn" style="display:inline-flex;align-items:center;gap:6px;font-size:12px;padding:3px 10px;border-radius:14px">${icon("sparkles")} Career Assistant</button>` : `<a class="btn btn-primary btn-sm" href="#/post-job" style="display:inline-flex;align-items:center;gap:6px;font-size:12px;padding:5px 12px;border-radius:14px">${icon("plus")} Post a job</a>`}<button class="icon-btn notification-button" aria-label="View notifications">${icon("bell")}<b class="unread-count" hidden></b></button><button class="icon-btn theme-toggle" aria-label="Toggle light or dark theme">&#9680;</button><div class="avatar small">${e(initials(name))}</div></div></header><main id="main-content" tabindex="-1">${content}</main><footer class="app-footer"><span>${recruiter ? "SkillMatch AI Talent Acquisition" : "Made for your next move."}</span><span>SkillMatch AI <span class="footer-dot">•</span> ${recruiter ? "Smart hiring, verified talent" : "Your career, in focus"} ${icon("sparkles")}</span></footer></div>`,
  );
  finish();
  workspace.updateBadge();
}
function jobAge(value?: string | null): string {
  return postedAge(value);
}

function finish(): void {
  createIcons({ icons });
  if (!reduced) {
    $(".stat-number").each(function () {
      const element = this;
      const label = element.dataset.value || "0";
      const state = { value: 0 };
      gsap.to(state, {
        value: parseFloat(label),
        duration: 1.1,
        ease: "power2.out",
        onUpdate: () => {
          element.textContent =
            Math.round(state.value) + (label.includes("%") ? "%" : "");
        },
      });
    });
  }
  if (!reduced) {
    gsap.from(".page-heading,.reveal", {
      y: 14,
      opacity: 0,
      duration: 0.55,
      stagger: 0.065,
      ease: "power2.out",
      clearProps: "all",
    });
  }
  $("a,button,input,select")
    .off("keydown.escape")
    .on("keydown.escape", (ev) => {
      if (ev.key === "Escape") $("body").removeClass("nav-open");
    });
}
function heading(
  eyebrow: string,
  title: string,
  subtitle: string,
  action = "",
): string {
  return `<div class="page-heading"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${subtitle}</p></div>${action}</div>`;
}
function sectionTitle(title: string, sub: string, action = ""): string {
  return `<div class="section-title"><div><h2>${title}</h2>${sub ? `<p>${sub}</p>` : ""}</div>${action}</div>`;
}
function companyLogo(company: string): string {
  let hue = 0;
  for (const c of company) hue = (hue * 31 + c.charCodeAt(0)) % 360;
  return `<div class="company-logo" style="background:linear-gradient(135deg,hsl(${hue} 55% 35%),hsl(${(hue + 50) % 360} 50% 20%));color:white">${e(initials(company))}</div>`;
}

function chip(skill: string, cls = ""): string {
  return `<span class="skill-chip ${cls}">${e(skill)}</span>`;
}
function jobCard(job: Job, _index = 0): string {
  const programBadge = job.program_badge
    ? `<span class="program-badge" style="display:inline-block;padding:2px 8px;font-size:11px;font-weight:600;border-radius:4px;background:rgba(121,82,245,0.15);color:var(--brand,#a78bfa);margin-bottom:6px">${e(job.program_badge)}</span>`
    : "";
  const confLabel = job.confidence_label || job.match?.confidence_label;
  const conf = job.confidence || job.match?.confidence || "low";
  const confidenceBadge = (job.score != null && confLabel)
    ? `<span class="confidence-badge ${conf}" style="font-size:11px;padding:2px 6px;border-radius:4px;margin-left:6px;${conf === "high" ? "background:rgba(34,197,94,0.15);color:#4ade80" : "background:rgba(234,179,8,0.15);color:#facc15"}">${e(confLabel)}</span>`
    : "";
  return `<article class="job-card reveal"><div class="job-card-top"><div class="company-info">${companyLogo(job.company)}<div><strong>${e(job.company)}</strong><span>${e(jobAge(job.posted_at))}</span></div></div><button class="icon-btn save-job ${job.saved ? "saved" : ""}" data-id="${job.id}" aria-label="${job.saved ? "Saved" : "Save"} ${e(job.title)}" aria-pressed="${Boolean(job.saved)}">${icon("bookmark")}</button></div>${programBadge}<a class="job-title" href="#/jobs/${job.id}">${e(job.title)}</a><div class="job-meta"><span>${icon("map-pin")}${e(job.location)}</span><span>${icon("clock-3")}${e(job.employment_type)}</span></div><div class="source-links">${(job.sources || []).map((source) => `<a href="${e(safeUrl(source.url))}" target="_blank" rel="noopener">${e(source.name)}</a>`).join(" · ") || e(job.is_demo ? "Demo posting" : job.source || "Native posting")}</div><div class="job-skills">${job.skills
    .slice(0, 3)
    .map((s) => chip(s))
    .join(
      "",
    )}${job.skills.length > 3 ? chip("+" + (job.skills.length - 3)) : ""}</div><div class="job-salary">${salary(job.salary_min, job.salary_max, job.salary_currency, job.salary_interval)}</div><div class="job-card-footer"><span class="match-pill">${icon("sparkles")}${job.score != null ? Math.round(job.score) + "% match" : "Explore role"}</span>${confidenceBadge}${safeUrl(job.apply_url) ? `<a class="text-link" href="${e(safeUrl(job.apply_url))}" target="_blank" rel="noopener">Apply ↗</a>` : ""}<a href="#/jobs/${job.id}" class="job-arrow" aria-label="View ${e(job.title)}">${icon("arrow-up-right")}</a></div></article>`;
}
function stats(): string {
  const values = [
    [
      "scan-line",
      "Job matches",
      analytics.matches,
      "Roles aligned with your skills",
      "violet",
    ],
    [
      "target",
      "Average match",
      analytics.average_score + "%",
      "Your skills are opening doors",
      "mint",
    ],
    [
      "send",
      "Applications",
      analytics.applications,
      "Every step brings you closer",
      "blue",
    ],
    [
      "messages-square",
      "Interviews",
      analytics.interviews,
      "Great conversations ahead",
      "peach",
    ],
  ];
  return `<div class="stats-grid">${values.map(([ic, label, val, note, color]) => `<div class="stat-card reveal"><div class="stat-heading"><span>${label}</span><span class="stat-icon ${color}">${icon(String(ic))}</span></div><div class="stat-value"><b class="stat-number" data-value="${val}">${val}</b></div><p>${note}</p></div>`).join("")}</div>`;
}
type MatchStatus = {
  active_jobs: number;
  scored_jobs: number;
  pending_jobs: number;
  requires_resume: boolean;
};
let matchingStatus: MatchStatus | null = null;
let dashboardRefresh: ReturnType<typeof setTimeout> | undefined;
function refreshDashboardLater() {
  clearTimeout(dashboardRefresh);
  const current = renderId;
  dashboardRefresh = setTimeout(
    async () => {
      if (current !== renderId || route() !== "dashboard") return;
      try {
        const previous = JSON.stringify([
          analytics,
          jobs,
          resumes,
          matchingStatus,
        ]);
        await loadCandidate();
        if (current !== renderId || route() !== "dashboard") return;
        if (
          previous !==
          JSON.stringify([analytics, jobs, resumes, matchingStatus])
        ) {
          cleanupScene?.();
          ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
          dashboard();
        } else refreshDashboardLater();
      } catch {
        if (current === renderId) refreshDashboardLater();
      }
    },
    matchingStatus?.pending_jobs ? 3000 : 15000,
  );
}
function matchingMessage(): string {
  if (!matchingStatus) return "";
  if (matchingStatus.active_jobs === 0) {
    return `<div class="panel worker-status-panel" style="padding:16px;margin-bottom:24px" role="status"><p class="subtle" style="margin:0">No jobs have been published yet. Your resume is saved; matches and average scores will appear when recruiter jobs or configured job feeds are available.</p></div>`;
  }
  if (matchingStatus.requires_resume) {
    return `<div class="panel worker-status-panel" style="padding:16px;margin-bottom:24px" role="status"><p class="subtle" style="margin:0">Upload your resume to calculate job matches and your average match score.</p></div>`;
  }
  const pct = Math.min(100, Math.round((matchingStatus.scored_jobs / (matchingStatus.active_jobs || 1)) * 100));
  if (matchingStatus.pending_jobs > 0) {
    return `<div class="panel worker-progress-card" role="status" style="padding:16px 20px;margin-bottom:24px"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px"><span><strong>Scoring matches…</strong> <small class="subtle" style="margin-left:6px">Worker active</small></span><span style="font-size:13px"><strong>${matchingStatus.scored_jobs}/${matchingStatus.active_jobs} scored</strong> (${pct}%)</span></div><div class="progress-bar-track" style="background:rgba(255,255,255,0.08);border-radius:999px;height:8px;overflow:hidden"><div class="progress-bar-fill" style="width:${pct}%;background:linear-gradient(90deg,var(--brand,#7952f5),#38bdf8);height:100%;transition:width 0.4s ease"></div></div></div>`;
  }
  return `<div class="panel worker-status-panel" style="padding:12px 18px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center"><small class="subtle">Scores reflect your latest resume across all ${matchingStatus.scored_jobs} active jobs.</small><span class="match-pill" style="font-size:12px">${icon("sparkles")} All scored</span></div>`;
}
async function loadCandidate(): Promise<void> {
  const [r, a, status] = await Promise.all([
    api<Resume[]>("/resumes"),
    api<Analytics>("/analytics"),
    api<MatchStatus>("/matches/status"),
  ]);
  resumes = r;
  analytics = a;
  matchingStatus = status;
}
async function loadDashboardJobs(activeRender: number): Promise<void> {
  try {
    if (resumes.length > 0) {
      const matchData = await api<Match[]>("/matches?page=1&size=6");
      if (activeRender !== renderId || route() !== "dashboard") return;
      jobs = matchData.map((m) => ({
        ...m.job,
        score: m.score,
        confidence: m.confidence,
        confidence_label: m.confidence_label,
      }));
      $("#dashboard-job-cards").html(
        jobs.slice(0, 3).map(jobCard).join("") ||
          empty(
            "Your matches are calculating",
            matchingStatus?.pending_jobs
              ? "The worker is scoring active opportunities against your skills. They will appear here shortly."
              : "No matched opportunities found yet.",
            "Browse all jobs",
            "jobs",
          ),
      );
      finish();
      return;
    }
    const data = await api<{ items: Job[] }>("/jobs?size=6");
    if (activeRender !== renderId || route() !== "dashboard") return;
    jobs = data.items;
    $("#dashboard-job-cards").html(
      jobs.slice(0, 3).map(jobCard).join("") ||
        empty(
          "Your next opportunity is on its way",
          "New jobs will appear here when recruiters post them.",
          "Browse jobs",
          "jobs",
        ),
    );
    finish();
  } catch {
    if (activeRender === renderId && route() === "dashboard")
      $("#dashboard-job-cards").html(
        empty(
          "Jobs could not load.",
          "Try Find jobs to retry.",
          "Find jobs",
          "jobs",
        ),
      );
  }
}

function dashboard(): void {
  refreshDashboardLater();
  const name = user?.name.split(" ")[0] || "there";
  shell(
    `${heading("A LITTLE CLARITY. A LOT OF POSSIBILITY.", `Your next move, ${e(name)}<span class="greeting-dot">.</span>`, `Let’s turn what you’re good at into where you’re going.`, `<a href="#/upload" class="btn btn-primary">${icon("upload")} Upload resume</a>`)}<div class="dashboard-hero reveal"><div class="hero-copy"><span class="hero-eyebrow"><span class="live-dot"></span> YOUR POTENTIAL, CONNECTED</span><h2>You bring the skills.<br>We find the <span>possibilities.</span></h2><p>Your experience is more than a document. Discover<br class="desktop-only"> opportunities that see the full picture.</p><a class="btn btn-light" href="#/matches">Explore my matches ${icon("arrow-up-right")}</a><span class="hero-footnote">${icon("sparkles")} A smarter match. A more meaningful next step.</span></div><div class="hero-visual" aria-label="Connected skills constellation"><div class="orbital-glow"></div><div id="skill-scene"></div><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="core-orb">${icon("sparkles")}</div><div class="floating-skill node-react">${icon("sparkles")} ${e(resumes[0]?.skills[0] || "Your skills")}</div><div class="floating-skill node-typescript">${e(resumes[0]?.skills[1] || "Your experience")}</div><div class="floating-skill node-design">${icon("sparkles")} ${e(resumes[0]?.skills[2] || "Your potential")}</div><div class="floating-skill node-python"><span>✳</span> Python</div><div class="float-dot dot-one"></div><div class="float-dot dot-two"></div><div class="constellation-caption"><span></span> Connecting your skills to what’s next</div></div></div>${stats()}${matchingMessage()}<div class="dashboard-columns"><section class="recommendations">${sectionTitle("Good things are a match", "Opportunities that feel like your next chapter.", `<a class="text-link" href="#/jobs">View all jobs ${icon("arrow-right")}</a>`)}<div class="jobs-grid" id="dashboard-job-cards"><div class="skeleton" aria-label="Loading recommended jobs"></div></div><div class="skills-panel panel reveal">${sectionTitle("Your skills, at a glance", "A strong foundation. Room to grow.", `<a class="text-link" href="#/analytics">View insights ${icon("arrow-up-right")}</a>`)}<div class="skills-panel-content"><div class="skills-overview"><div class="skill-legend"><span><i class="legend-dot purple"></i> Your strengths</span><span class="subtle">${resumes[0]?.skills.length || 0} skills identified</span></div><div class="strength-chips">${
      (resumes[0]?.skills || [])
        .slice(0, 8)
        .map((s) => chip(s, "strength"))
        .join("") ||
      '<p class="subtle">Upload a resume to discover your strengths.</p>'
    }</div><div class="skills-tip">${icon("lightbulb")}<span>Your next opportunity could be one new skill away.</span></div></div><div class="gap-overview"><div class="skill-legend"><span><i class="legend-dot cyan"></i> Skills worth adding</span><span class="subtle">In your matched roles</span></div>${
      Object.entries(analytics.skill_gaps)
        .slice(0, 3)
        .map(
          ([s, n], i) =>
            `<div class="gap-row"><span>${e(s)}</span><div class="gap-track"><div style="width:${Math.min(100, (n / (Object.values(analytics.skill_gaps)[0] || 1)) * 85)}%;opacity:${1 - i * 0.18}"></div></div><span>${n} roles</span></div>`,
        )
        .join("") ||
      '<p class="subtle">Analyze a job match to see learning priorities.</p>'
    }</div></div></div></section><aside class="right-column"><div class="resume-panel panel reveal"><div class="section-title"><h2>Your resume</h2><span class="status-label"><span></span>${resumes.length ? "Analyzed" : "Get started"}</span></div><div class="resume-file"><span class="file-icon">${icon("file-text")}</span><div><strong>${resumes.length ? e(resumes[0].filename) : "Add your experience"}</strong><span>${resumes.length ? "Your career story, in one place" : "PDF or DOCX · Up to 5 MB"}</span></div></div><div class="resume-divider"></div><div class="resume-score"><div class="skill-count" ><span>${resumes.length ? resumes[0].skills.length : 0}</span></div><div><strong>${resumes.length ? "You have a strong foundation" : "Let’s find your strengths"}</strong><p>${resumes.length ? "Skills discovered in your resume. Ready for your next move." : "Upload your resume for a personal skill breakdown."}</p></div></div><a href="#/upload" class="btn btn-outline w-100">${icon("file-pen-line")} ${resumes.length ? "Manage resume" : "Upload resume"} ${icon("arrow-right")}</a></div><div class="learning-panel panel reveal"><div class="section-title"><h2>A little learning. A big leap.</h2><span class="tiny-spark">${icon("sparkles")}</span></div><p>Build the skills that open more doors.</p><div id="dashboard-learning-items">${learningItems()}</div><a href="#/analytics" class="text-link learning-link">Explore your skill gaps ${icon("arrow-right")}</a></div><div class="quote-card reveal"><span>“</span><p>The best way to predict your<br>future is to create it.</p><small>YOUR NEXT CHAPTER IS WAITING</small><div class="quote-star">✳</div></div></aside></div>`,
    "Overview",
  );
  mountScene();
  const activeRender = renderId;
  void loadDashboardJobs(activeRender);
  void workspace
    .loadLearning()
    .then(() => {
      if (activeRender === renderId && route() === "dashboard")
        $("#dashboard-learning-items").html(learningItems());
    })
    .catch(() => {
      if (activeRender === renderId && route() === "dashboard")
        $("#dashboard-learning-items").html(
          '<p class="subtle">Learning resources could not load right now.</p>',
        );
    });
}
function empty(
  title: string,
  text: string,
  button = "",
  path = "upload",
): string {
  return `<div class="empty-state">${icon("sparkles")}<h2>${title}</h2><p>${text}</p>${button ? `<a class="btn btn-primary" href="#/${path}">${button}${icon("arrow-right")}</a>` : ""}</div>`;
}
async function mountScene(): Promise<void> {
  const el = document.getElementById("skill-scene");
  if (!el || reduced || navigator.hardwareConcurrency <= 2) return;
  const id = renderId;
  try {
    const { createScene } = await import("./lib/scene");
    if (id === renderId) cleanupScene = createScene(el);
  } catch {
    /* CSS constellation remains available without WebGL. */
  }
}
function uploadPage(): void {
  shell(
    `${heading("YOUR EXPERIENCE. YOUR POTENTIAL.", "Let your skills speak.", "Upload your resume. We’ll connect the dots.")}<div class="upload-layout"><section class="panel upload-panel reveal"><span class="step-label">01 / YOUR RESUME</span><h2>A small upload. A big first step.</h2><p>We’ll extract your skills and help you find the right opportunities.</p><form id="upload-form"><label class="dropzone" for="resume-file" tabindex="0"><span class="upload-orb">${icon("cloud-upload")}</span><strong>Drop your resume here</strong><span>or <b>browse files</b> from your device</span><small>PDF or DOCX · Maximum 5 MB</small><input id="resume-file" name="resume" type="file" accept=".pdf,.docx" class="visually-hidden"></label><div id="selected-file" aria-live="polite"></div><div class="privacy-note">${icon("shield-check")} Your resume is private. Recruiters only see your name and match score when you apply.</div><button class="btn btn-primary w-100" type="submit">Analyze my resume ${icon("sparkles")}</button><div class="form-error" role="alert"></div></form></section><aside><div class="panel upload-explainer reveal"><span class="eyebrow">A CLEARER PICTURE</span><h2>More than keywords.</h2>${[
      [
        "file-scan",
        "Read between the lines",
        "We extract skills from your experience using natural language processing.",
      ],
      [
        "scan-line",
        "Find your fit",
        "Semantic similarity and skill overlap help surface relevant roles.",
      ],
      [
        "route",
        "See a path forward",
        "Understand your gaps and discover what to learn next.",
      ],
    ]
      .map(
        ([ic, t, d], i) =>
          `<div class="explain-step"><span>${icon(ic)}</span><div><small>0${i + 1}</small><h3>${t}</h3><p>${d}</p></div></div>`,
      )
      .join("")}</div>${
      resumes.length
        ? `<div class="panel existing-resume"><h3>Your uploaded resumes</h3><div style="display:flex;flex-direction:column;gap:16px;margin-top:12px">${resumes
            .map(
              (r) =>
                `<div class="resume-card-item" style="border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:12px;background:rgba(255,255,255,0.02)">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px">
                    <div>
                      <strong style="font-size:14px">${e(r.filename)}</strong>
                      <div style="font-size:12px;color:rgba(255,255,255,0.5)">Uploaded ${e(new Date(r.created_at).toLocaleDateString())}</div>
                    </div>
                    <div>
                      ${r.is_primary ? '<span class="badge" style="background:#10b981;color:#fff;font-size:11px;padding:2px 8px;border-radius:12px">★ Active primary</span>' : `<button class="btn btn-outline btn-sm set-primary-resume" data-id="${r.id}" style="font-size:11px;padding:2px 8px">Set as primary</button>`}
                    </div>
                  </div>
                  <div class="strength-chips" style="margin-top:8px">${r.skills.slice(0, 8).map((s) => chip(s, "strength")).join("")}</div>
                  ${r.parse_warnings && r.parse_warnings.length ? `<div class="parse-warnings" style="margin-top:10px;padding:8px 12px;background:rgba(245,158,11,0.08);border-left:3px solid #f59e0b;border-radius:4px;font-size:12px;color:#f59e0b;"><strong style="display:block;margin-bottom:4px">⚠️ ATS Suggestions:</strong><ul style="margin:0 0 0 16px;padding:0">${r.parse_warnings.map((w) => `<li>${e(w)}</li>`).join("")}</ul></div>` : ""}
                  ${user ? `<div style="margin-top:8px;text-align:right"><button class="text-link danger delete-resume" data-id="${r.id}" style="font-size:12px">Delete resume ${icon("trash-2")}</button></div>` : ""}
                </div>`,
            )
            .join("")}</div></div>`
        : ""
    }</aside></div>`,
    "My resume",
  );
}
let nextCursor: number | null = null;
let searchVersion = 0;
let jobObserver: IntersectionObserver | undefined;
let jobsLoading = false;
function renderFilterChips(): void {
  const form = $("#job-search");
  if (!form.length) return;
  const chips: string[] = [];
  const q = String(form.find("[name=q]").val() || "").trim();
  const location = String(form.find("[name=location]").val() || "").trim();
  const country = String(form.find("[name=country]").val() || "").trim();
  const exp = String(form.find("[name=experience_level]").val() || "").trim();
  const kind = String(form.find("[name=kind]").val() || "").trim();
  const remote = form.find("[name=remote]").is(":checked");
  const salary = form.find("[name=salary_disclosed]").is(":checked");
  const days = String(form.find("[name=days]").val() || "").trim();

  if (q) chips.push(`<span class="filter-chip"><span>Query: "${e(q)}"</span><button type="button" class="remove-chip-btn" data-field="q" aria-label="Remove keyword filter">✕</button></span>`);
  if (location) chips.push(`<span class="filter-chip"><span>City: "${e(location)}"</span><button type="button" class="remove-chip-btn" data-field="location" aria-label="Remove location filter">✕</button></span>`);
  if (country && country !== "India + Remote worldwide") chips.push(`<span class="filter-chip"><span>Country: ${e(country)}</span><button type="button" class="remove-chip-btn" data-field="country" aria-label="Remove country filter">✕</button></span>`);
  if (exp) chips.push(`<span class="filter-chip"><span>Level: ${e(exp)}</span><button type="button" class="remove-chip-btn" data-field="experience_level" aria-label="Remove level filter">✕</button></span>`);
  if (kind) chips.push(`<span class="filter-chip"><span>Type: ${e(kind)}</span><button type="button" class="remove-chip-btn" data-field="kind" aria-label="Remove job type filter">✕</button></span>`);
  if (remote) chips.push(`<span class="filter-chip"><span>Remote only</span><button type="button" class="remove-chip-btn" data-field="remote" aria-label="Remove remote filter">✕</button></span>`);
  if (salary) chips.push(`<span class="filter-chip"><span>Salary disclosed</span><button type="button" class="remove-chip-btn" data-field="salary_disclosed" aria-label="Remove salary filter">✕</button></span>`);
  if (days) chips.push(`<span class="filter-chip"><span>Within ${days} days</span><button type="button" class="remove-chip-btn" data-field="days" aria-label="Remove days filter">✕</button></span>`);

  $("#active-filter-chips").html(chips.join(""));
}

async function jobsPage(): Promise<void> {
  const params = new URLSearchParams(location.hash.split("?")[1] || "");
  const countryParam = params.get("country");
  const defaultCountry = countryParam !== null ? countryParam : "India + Remote worldwide";

  shell(
    `${heading("FIND YOUR NEXT CHAPTER.", "Good work starts with a good fit.", "Explore roles that value what you bring.")}<div class="nl-search-bar" style="margin-bottom:14px;display:flex;gap:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:8px 12px;align-items:center;"><span style="font-size:16px">✨</span><input id="nl-search-input" style="flex:1;background:transparent;border:none;color:#fff;outline:none;font-size:13px" placeholder="Try natural language search: 'remote Python ML internships in India' or 'senior react frontend'..."><button type="button" class="btn btn-primary btn-sm" id="btn-nl-search" style="font-size:12px;padding:4px 12px">Search with AI</button></div><div id="ai-filters-applied" style="margin-bottom:10px;font-size:12px;color:#10b981;font-weight:600" hidden></div><div id="active-filter-chips" class="active-filter-chips"></div><form id="job-search" class="search-panel panel"><div class="search-field" style="min-width:180px;flex:1 1 200px"><input name="q" aria-label="Job title, company, or skill" placeholder="Job title, company, or skill" value="${e(params.get("q") || "")}"></div><div class="search-field" style="min-width:160px;flex:1 1 180px"><input name="location" aria-label="Location" placeholder="City or region" value="${e(params.get("location") || "")}"></div><select name="country" aria-label="Country"><option value="India + Remote worldwide" ${defaultCountry === "India + Remote worldwide" ? "selected" : ""}>India + Remote worldwide (Default)</option><option value="India" ${defaultCountry === "India" ? "selected" : ""}>India only</option><option value="" ${defaultCountry === "" ? "selected" : ""}>All Countries (Worldwide)</option><option value="United States" ${defaultCountry === "United States" ? "selected" : ""}>United States</option><option value="United Kingdom" ${defaultCountry === "United Kingdom" ? "selected" : ""}>United Kingdom</option><option value="Germany" ${defaultCountry === "Germany" ? "selected" : ""}>Germany</option><option value="Canada" ${defaultCountry === "Canada" ? "selected" : ""}>Canada</option></select><select name="experience_level" aria-label="Experience level"><option value="">All Experience</option><option value="intern" ${params.get("experience_level") === "intern" ? "selected" : ""}>Internship</option><option value="entry" ${params.get("experience_level") === "entry" ? "selected" : ""}>Entry-Level / Fresher</option><option value="mid" ${params.get("experience_level") === "mid" ? "selected" : ""}>Mid-Level</option><option value="senior" ${params.get("experience_level") === "senior" ? "selected" : ""}>Senior</option></select><select name="kind" aria-label="Job type"><option value="">All job types</option>${["Full-time", "Part-time", "Contract", "Internship"].map((v) => `<option ${params.get("kind") === v ? "selected" : ""}>${v}</option>`).join("")}</select><select name="days" aria-label="Posted within"><option value="">Any time</option>${[["7", "Posted within 7 days"], ["30", "Posted within 30 days"], ["90", "Posted within 90 days"], ["120", "Posted within 120 days"]].map(([v, l]) => `<option value="${v}" ${params.get("days") === v ? "selected" : ""}>${l}</option>`).join("")}</select><select name="sort" aria-label="Sort by"><option value="recent" ${params.get("sort") !== "relevance" ? "selected" : ""}>Sort by: Most recent</option><option value="relevance" ${params.get("sort") === "relevance" ? "selected" : ""}>Sort by: Relevance</option></select><label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;white-space:nowrap"><input type="checkbox" name="remote" value="true" ${params.get("remote") === "true" ? "checked" : ""}> Remote</label><label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;cursor:pointer;white-space:nowrap"><input type="checkbox" name="salary_disclosed" value="true" ${params.get("salary_disclosed") === "true" ? "checked" : ""}> Salary disclosed</label><label style="display:inline-flex;align-items:center;gap:6px;font-size:13px;white-space:nowrap">Min match<input name="min_match" type="number" min="0" max="100" value="${e(params.get("min_match") || "0")}"></label><button class="btn btn-primary">Find roles</button></form><div class="jobs-toolbar"><span id="jobs-count" role="status">Loading opportunities…</span>${user?.role === "candidate" ? '<button class="text-link save-search">Save this search</button>' : ""}<a class="text-link" href="#/applications">My saved jobs</a></div><div id="widen-container"></div><div id="job-results" class="all-jobs-grid"><div class="skeleton"></div><div class="skeleton"></div></div><div id="pagination" class="pagination-controls"></div>`,
    "Find jobs",
  );
  await searchJobs();
}

async function searchJobs(append = false): Promise<void> {
  if (append && (jobsLoading || nextCursor === null)) return;
  jobObserver?.disconnect();
  const version = append ? searchVersion : ++searchVersion;
  const pageRender = renderId;
  jobsLoading = true;
  const form = $("#job-search");
  const query = new URLSearchParams({
    q: String(form.find("[name=q]").val() || ""),
    location: String(form.find("[name=location]").val() || ""),
    kind: String(form.find("[name=kind]").val() || ""),
    min_match: String(form.find("[name=min_match]").val() || 0),
    size: "12",
  });
  const countryVal = String(form.find("[name=country]").val() || "");
  const expVal = String(form.find("[name=experience_level]").val() || "");
  const remoteVal = form.find("[name=remote]").is(":checked");
  const salaryDisclosedVal = form.find("[name=salary_disclosed]").is(":checked");
  if (countryVal) query.set("country", countryVal);
  if (expVal) query.set("experience_level", expVal);
  if (remoteVal) query.set("remote", "true");
  if (salaryDisclosedVal) query.set("salary_disclosed", "true");
  const daysVal = String(form.find("[name=days]").val() || "");
  const sortVal = String(form.find("[name=sort]").val() || "recent");
  if (daysVal) query.set("days", daysVal);
  if (sortVal) query.set("sort", sortVal);
  if (append && nextCursor) query.set("cursor", String(nextCursor));
  if (!append)
    $("#job-results").html(
      '<div class="skeleton" aria-label="Loading jobs"></div>',
    );
  renderFilterChips();
  try {
    const data = await api<{
      items: Job[];
      total: number;
      next_cursor: number | null;
      requires_resume: boolean;
    }>(`/jobs?${query}`);
    if (version !== searchVersion || pageRender !== renderId) return;
    nextCursor = data.next_cursor;
    $("#jobs-count").text(
      `${data.total} active opportunities${data.requires_resume ? " · Upload a resume for personalized scores" : ""}`,
    );

    // Suggest widening if fewer than 10 results and country filter applied
    if (data.total < 10 && countryVal && countryVal !== "") {
      $("#widen-container").html(
        `<div class="widen-suggestion"><span>Found only ${data.total} role${data.total === 1 ? "" : "s"} for "${e(countryVal)}". Widen search to include worldwide remote roles?</span><button type="button" class="btn btn-outline btn-sm btn-widen-worldwide" style="font-size:11px;padding:3px 10px">Show worldwide remote</button></div>`,
      );
    } else {
      $("#widen-container").empty();
    }

    if (append) $("#job-results").append(data.items.map(jobCard).join(""));
    else if (data.items.length) {
      $("#job-results").html(data.items.map(jobCard).join(""));
    } else {
      // Meaningful empty state
      const hasFilters = Boolean(
        query.get("q") ||
          query.get("location") ||
          query.get("kind") ||
          countryVal ||
          expVal ||
          remoteVal ||
          salaryDisclosedVal ||
          Number(query.get("min_match")) > 0,
      );
      if (hasFilters) {
        const primaryFilter = query.get("q")
          ? { field: "q", label: `keyword "${query.get("q")}"` }
          : countryVal && countryVal !== ""
            ? { field: "country", label: `country "${countryVal}"` }
            : query.get("location")
              ? { field: "location", label: `location "${query.get("location")}"` }
              : remoteVal
                ? { field: "remote", label: "remote only" }
                : expVal
                  ? { field: "experience_level", label: `experience level "${expVal}"` }
                  : { field: "all", label: "selected criteria" };

        $("#job-results").html(
          `<div class="empty-state">${icon("sparkles")}<h2>No opportunities match your current filters.</h2><p>Your filter on <strong>${e(primaryFilter.label)}</strong> narrowed the results to 0. Remove this filter or browse worldwide remote roles to find active positions.</p><div style="display:flex;gap:8px;justify-content:center;margin-top:14px;flex-wrap:wrap"><button type="button" class="btn btn-outline btn-sm btn-remove-filter" data-field="${primaryFilter.field}">Remove ${e(primaryFilter.label)}</button><button type="button" class="btn btn-primary btn-sm btn-widen-worldwide">Show worldwide remote jobs</button><button type="button" class="btn btn-outline btn-sm btn-clear-all-filters">Clear all filters</button></div></div>`,
        );
      } else {
        $("#job-results").html(
          empty(
            "No jobs published yet.",
            "No jobs have been published yet. A resume upload does not create job listings. Recruiters can publish jobs, or an administrator can configure a job feed.",
          ),
        );
      }
    }
    $("#pagination").html(
      nextCursor
        ? '<button class="btn btn-outline load-more-jobs">Load more opportunities</button>'
        : "",
    );
    if (nextCursor) {
      jobObserver = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting))
            void searchJobs(true);
        },
        { rootMargin: "150px" },
      );
      jobObserver.observe(document.querySelector("#pagination")!);
    }
    finish();
  } catch (error) {
    if (version === searchVersion && pageRender === renderId) {
      $("#pagination").html(
        '<button class="btn btn-outline retry-jobs">Retry loading jobs</button>',
      );
      if (!append)
        $("#job-results").html(
          empty("Unable to load jobs.", e((error as Error).message)),
        );
      else toast((error as Error).message, "error");
    }
  } finally {
    if (version === searchVersion) jobsLoading = false;
  }
}
async function jobDetail(id: number): Promise<void> {
  await workspace.detail(id);
}

async function matchesPage(): Promise<void> {
  const pageRender = renderId;
  const first = await api<Match[]>("/matches?page=1&size=12");
  if (pageRender !== renderId) return;
  matches = first;
  shell(
    `${heading("YOUR SKILLS, IN THE RIGHT PLACE.", "A match with more meaning.", "Understand the fit and what comes next.")}<div class="all-jobs-grid" id="match-results">${first.map((m) => jobCard({ ...m.job, score: m.score, confidence: m.confidence, confidence_label: m.confidence_label })).join("") || empty("Your first match is one step away.", "Choose a role and analyze how your resume fits.", "Explore opportunities", "jobs")}</div><div id="match-pagination">${first.length === 12 ? '<button class="btn btn-outline load-more-matches" data-page="2">Load more matches</button>' : ""}</div>`,
    "My matches",
  );
}

function matchPage(match: Match): void {
  void workspace.detail(match.job_id);
}

async function analyticsPage(): Promise<void> {
  await workspace.insights();
}

async function renderCharts(kind: string, match?: Match): Promise<void> {
  const id = renderId;
  const { mountCharts } = await import("./lib/charts");
  if (id === renderId)
    cleanupCharts = mountCharts(kind, analytics, match, reduced);
}
let cachedCandidates: CandidateProfile[] = [];
let activeCandidateTab: "pool" | "applicants" = "pool";
let candidateFilterSkill = "";
let candidateSearchQuery = "";

function renderTalentPool(): string {
  let list = cachedCandidates;
  if (candidateSearchQuery.trim()) {
    const q = candidateSearchQuery.trim().toLowerCase();
    list = list.filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.skills.some((s) => s.toLowerCase().includes(q)) ||
        c.headline.toLowerCase().includes(q) ||
        c.snippet.toLowerCase().includes(q),
    );
  }
  if (candidateFilterSkill) {
    const s = candidateFilterSkill.toLowerCase();
    list = list.filter((c) => c.skills.some((sk) => sk.toLowerCase() === s));
  }
  if (!list.length) {
    return `<div class="panel" style="padding:48px 24px;text-align:center;grid-column:1/-1"><p class="subtle" style="font-size:16px;margin:0 0 12px 0">No candidates match your search filter.</p><button class="btn btn-outline btn-sm" id="btn-clear-cand-filters">Clear filters</button></div>`;
  }
  return list
    .map(
      (c) =>
        `<div class="panel candidate-card"><div class="candidate-header"><div class="avatar">${e(initials(c.name))}</div><div><strong>${e(c.name)}</strong><span>${e(c.headline || "Candidate")}</span></div><span class="match-pill">${icon("sparkles")} ${c.match_score ? Math.round(c.match_score) + "% match" : "Verified"}</span></div><p class="candidate-snippet">${e(c.snippet)}</p><div class="candidate-meta"><span class="experience-badge">${icon("clock-3")} ${c.experience_years}y experience</span><div class="strength-chips">${c.skills.slice(0, 5).map((s) => chip(s)).join("")}${c.skills.length > 5 ? chip("+" + (c.skills.length - 5)) : ""}</div></div><div class="candidate-footer"><button class="btn btn-outline btn-sm view-candidate-btn" data-id="${c.id}">View resume</button><a class="btn btn-primary btn-sm" href="mailto:${e(c.email)}?subject=Opportunity%20via%20SkillMatch">Contact ${icon("arrow-up-right")}</a></div></div>`,
    )
    .join("");
}

async function applicationsPage(): Promise<void> {
  const pageRender = renderId;
  if (user?.role === "candidate") {
    await workspace.tracker();
    return;
  }
  const [candidatesData, applications] = await Promise.all([
    api<CandidateProfile[]>("/candidates"),
    api<Application[]>("/applications"),
  ]);
  cachedCandidates = candidatesData;
  if (pageRender !== renderId) return;

  const topSkills = [
    "Python",
    "React",
    "TypeScript",
    "Docker",
    "DevOps",
    "Machine Learning",
    "SQL",
    "Go",
  ];

  shell(
    `${heading(
      "ONE STEP CLOSER. EVERY TIME.",
      "Meet your next great hire.",
      "Discover verified candidates from the talent pool, or review incoming applicants.",
      `<a class="btn btn-primary" href="#/post-job">${icon("plus")} Post a job</a>`,
    )}<div class="candidate-tabs-bar"><button class="candidate-tab-btn ${activeCandidateTab === "pool" ? "active" : ""}" data-tab="pool">${icon("users")} Talent Pool (${candidatesData.length})</button><button class="candidate-tab-btn ${activeCandidateTab === "applicants" ? "active" : ""}" data-tab="applicants">${icon("layers")} Direct Applicants (${applications.length})</button></div><div id="talent-pool-view" style="${activeCandidateTab === "pool" ? "" : "display:none"}"><div class="candidate-filter-bar"><div class="candidate-search-wrap">${icon("search")}<input type="text" id="candidate-search" placeholder="Search candidate by name, skill, or experience..." value="${e(candidateSearchQuery)}"></div><div class="candidate-skill-pills"><span style="font-size:12px;color:var(--muted);font-weight:600">Quick Filter:</span><button class="skill-filter-pill ${!candidateFilterSkill ? "active" : ""}" data-skill="">All skills</button>${topSkills.map((sk) => `<button class="skill-filter-pill ${candidateFilterSkill.toLowerCase() === sk.toLowerCase() ? "active" : ""}" data-skill="${sk}">${sk}</button>`).join("")}</div></div><div class="candidates-pool-grid" id="candidates-pool-cards">${renderTalentPool()}</div></div><div id="direct-applicants-view" style="${activeCandidateTab === "applicants" ? "" : "display:none"}"><div class="panel table-panel"><div class="table-responsive"><table class="app-table"><thead><tr><th>Candidate</th><th>Applied Role</th><th>Match fit</th><th>Status</th><th>Applied date</th></tr></thead><tbody>${applications.map((a) => `<tr><td><strong>${e(a.candidate)}</strong></td><td>${e(a.job.title)}</td><td><span class="match-pill">${a.score === null ? "Pending" : Math.round(a.score) + "%"}</span></td><td><select class="status-select" data-id="${a.id}" aria-label="Application status">${["Applied", "Reviewing", "Interview", "Offer", "Rejected", "Hired"].map((s) => `<option ${s === a.status ? "selected" : ""}>${s}</option>`).join("")}</select></td><td>${new Date(a.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</td></tr>`).join("")}</tbody></table></div>${!applications.length ? empty("No direct applicants yet.", "Candidates who apply to your job postings will appear here in the pipeline. Browse the talent pool above to contact candidates directly.", "View Talent Pool", "candidates") : ""}</div></div>`,
    "Candidates",
  );
}
function authPage(register = false): void {
  $("#app").html(
    `<main class="auth-layout" id="main-content"><div class="auth-story">${logo()}<div><span class="hero-eyebrow"><span class="live-dot"></span> THE NEXT CHAPTER IS YOURS</span><h1>You’re more than<br>a <span>resume.</span></h1><p>Find the opportunities that see what you bring.<br>And the possibilities you haven’t seen yet.</p><div class="auth-art"><div class="orbit orbit-one"></div><div class="core-orb">${icon("sparkles")}</div><span class="floating-skill node-react">${icon("atom")} Your skills</span><span class="floating-skill node-design">${icon("briefcase-business")} Your next move</span></div></div><span class="auth-story-footer">A little clarity. A big step forward.</span></div><div class="auth-form-side"><a class="back-link" href="#/dashboard">${icon("arrow-left")} Explore the workspace</a><form id="auth-form" data-mode="${register ? "register" : "login"}"><span class="eyebrow">${register ? "POSSIBILITIES START HERE" : "GOOD TO SEE YOU AGAIN"}</span><h2>${register ? "Make your next move." : "Welcome back."}</h2><p>${register ? "A clearer path to work that fits you." : "Your next chapter is right where you left it."}</p>${register ? '<label for="name">Your name</label><input id="name" name="name" required minlength="2" maxlength="100" autocomplete="name" placeholder="Alex Morgan">' : ""}<label for="email">Email address</label><input id="email" name="email" type="email" required autocomplete="email" placeholder="you@example.com"><label for="password">Password</label><div class="password-field"><input id="password" name="password" type="password" required minlength="${register ? 10 : 1}" maxlength="128" autocomplete="${register ? "new-password" : "current-password"}" placeholder="${register ? "At least 10 characters" : "Your password"}"><button type="button" class="icon-btn toggle-password" aria-label="Show password">${icon("eye")}</button></div>${register ? '<label for="role">I’m here to</label><select id="role" name="role"><option value="candidate">Find my next opportunity</option><option value="recruiter">Find great people</option></select>' : ""}<div class="form-error" role="alert"></div><button class="btn btn-primary w-100" type="submit">${register ? "Create my account" : "Sign in"} ${icon("arrow-right")}</button><div class="auth-switch">${register ? "Already part of SkillMatch?" : "New here?"} <a href="#/${register ? "login" : "register"}">${register ? "Sign in" : "Create an account"}</a></div><div class="auth-divider"><span>just looking around?</span></div><a href="#/jobs" class="btn btn-outline w-100">Browse public jobs ${icon("arrow-up-right")}</a></form><small class="auth-privacy">${icon("shield-check")} Your career story stays yours.</small></div></main>`,
  );
  finish();
}
function landing(): void {
  $("#app").html(
    `<div class="landing">
      <header class="landing-nav">
        ${logo()}
        <nav aria-label="Public navigation">
          <a href="#how-it-works" class="scroll-link">How it works</a>
          <a href="#/jobs">Explore jobs</a>
          <a href="#/login">Sign in</a>
          <a href="#/register" class="btn btn-primary">Find my next move ${icon("arrow-up-right")}</a>
        </nav>
      </header>
      <main id="main-content">
        <section class="landing-hero">
          <div class="landing-hero-copy">
            <span class="hero-eyebrow"><span class="live-dot"></span> A LITTLE CLARITY. A WORLD OF POSSIBILITY.</span>
            <h1>Your skills.<br>Your potential.<br><span>Your next chapter.</span></h1>
            <p>You bring more to the table than a list of keywords. Discover transparent job opportunities that see the full picture of what you can do.</p>
            <div class="landing-buttons">
              <a href="#/register" class="btn btn-primary magnetic">Discover where you belong ${icon("arrow-up-right")}</a>
              <a href="#/jobs" class="btn btn-outline">Explore live jobs ${icon("arrow-right")}</a>
            </div>
            <div class="landing-proof">
              ${icon("shield-check")} Private by design <span>•</span> Transparent matching <span>•</span> Built around you
            </div>
          </div>
          <div class="landing-scene">
            <div id="skill-scene"></div>
            <div class="orbital-glow"></div>
            <div class="orbit orbit-one"></div>
            <div class="orbit orbit-two"></div>
            <div class="core-orb">${icon("sparkles")}</div>
            <div class="floating-skill node-react">${icon("atom")} React</div>
            <div class="floating-skill node-typescript"><b>TS</b> TypeScript</div>
            <div class="floating-skill node-design">${icon("figma")} Design</div>
            <div class="floating-skill node-python">${icon("code-2")} Python</div>
          </div>
          <span class="scroll-cue">A clearer path starts here ${icon("arrow-down")}</span>
        </section>

        <section class="landing-companies">
          <span>OPPORTUNITIES CONNECTED TO LEADING TEAMS</span>
          <div>
            <span>Google</span>
            <span>Stripe</span>
            <span>Razorpay</span>
            <span>Linear</span>
            <span>Vercel</span>
          </div>
          <small>Connecting verified talents with forward-thinking engineering teams</small>
        </section>

        <section id="how-it-works" class="story-section">
          <div class="story-heading">
            <span class="eyebrow">FROM WHAT YOU KNOW TO WHERE YOU GO</span>
            <h2>A clearer path.<br>Three simple steps.</h2>
            <p>Less guesswork. More possibility. Transparent skill intelligence designed for your growth and verified fit.</p>
          </div>
          <div class="story-steps">
            ${[
              [
                "01",
                "file-scan",
                "Start with your story.",
                "Upload your resume in PDF or Word. Our NLP parser extracts 310+ standardized skills woven through your actual experience.",
              ],
              [
                "02",
                "scan-line",
                "See where you fit.",
                "Understand exactly why you match every role with hybrid semantic embeddings and transparent percentage breakdowns.",
              ],
              [
                "03",
                "sprout",
                "Grow into what’s next.",
                "Get a crystal clear picture of your strengths, real-time ATS suggestions, and practical learning resources to close skill gaps.",
              ],
            ]
              .map(
                ([n, i, t, p]) =>
                  `<article class="story-step"><span class="story-number">${n}</span><span class="story-icon">${icon(i)}</span><h3>${t}</h3><p>${p}</p></article>`,
              )
              .join("")}
          </div>
        </section>

        <section class="landing-features">
          <div class="landing-features-header">
            <span class="eyebrow">BUILT FOR HUMANS, NOT KEYWORD BOTS</span>
            <h2>Why candidates choose SkillMatch</h2>
            <p>Traditional hiring algorithms discard resumes over missing buzzwords. SkillMatch understands your real context.</p>
          </div>
          <div class="features-grid">
            <div class="feature-card">
              <div class="feature-icon">${icon("target")}</div>
              <h3>Explainable Matching</h3>
              <p>Every score is backed by visible skill overlaps and semantic relevance. Never wonder why you matched or missed out.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">${icon("shield-check")}</div>
              <h3>Privacy-First Profile</h3>
              <p>Recruiters only see your qualifications and anonymized skills until you actively choose to submit an application.</p>
            </div>
            <div class="feature-card">
              <div class="feature-icon">${icon("lightbulb")}</div>
              <h3>Actionable Skill Gaps</h3>
              <p>Turn rejections into roadmaps. Direct links to free curated learning resources for every in-demand role requirement.</p>
            </div>
          </div>
        </section>

        <section class="landing-cta">
          <div class="cta-inner">
            <span class="eyebrow">YOUR FUTURE ISN’T A KEYWORD.</span>
            <h2>Let’s find where<br>you <span>belong.</span></h2>
            <p>Join candidates discovering work that aligns with their actual experience and ambitions.</p>
            <div class="landing-buttons" style="justify-content:center">
              <a href="#/register" class="btn btn-primary">Make my next move ${icon("arrow-up-right")}</a>
              <a href="#/jobs" class="btn btn-outline">Explore live openings ${icon("arrow-right")}</a>
            </div>
          </div>
        </section>
      </main>
      <footer class="landing-footer">
        ${logo()}
        <span>Made for your next move. · SkillMatch AI</span>
        <a href="#/dashboard">Explore the workspace ${icon("arrow-up-right")}</a>
      </footer>
    </div>`,
  );
  finish();
  mountScene();
  if (!reduced) {
    gsap.utils.toArray<HTMLElement>(".story-step").forEach((el) => {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: "top 90%" },
        opacity: 0,
        y: 30,
        duration: 0.6,
        clearProps: "all",
      });
    });
    gsap.utils.toArray<HTMLElement>(".feature-card").forEach((el) => {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: "top 90%" },
        opacity: 0,
        y: 25,
        duration: 0.5,
        clearProps: "all",
      });
    });
    gsap.to(".landing-scene", {
      y: 80,
      scrollTrigger: {
        trigger: ".landing-hero",
        start: "top top",
        end: "bottom top",
        scrub: 1,
      },
    });
  }
}
function recruiterStats(
  jobsCount: number,
  candsCount: number,
  appsCount: number,
  avgScore: number,
): string {
  const values = [
    [
      "briefcase-business",
      "Active roles",
      jobsCount,
      "Open roles accepting candidates",
      "violet",
    ],
    [
      "users",
      "Candidate pool",
      candsCount,
      "Verified profiles with parsed resumes",
      "mint",
    ],
    [
      "layers",
      "Direct applicants",
      appsCount,
      "Candidates in review pipeline",
      "blue",
    ],
    [
      "target",
      "Average fit",
      Math.round(avgScore) + "%",
      "Skills & qualification match",
      "peach",
    ],
  ];
  return `<div class="stats-grid">${values.map(([ic, label, val, note, color]) => `<div class="stat-card reveal"><div class="stat-heading"><span>${label}</span><span class="stat-icon ${color}">${icon(String(ic))}</span></div><div class="stat-value"><b class="stat-number" data-value="${val}">${val}</b></div><p>${note}</p></div>`).join("")}</div>`;
}

async function recruiterPage(): Promise<void> {
  const pageRender = renderId;
  if (!user) {
    authPage();
    return;
  }
  const [data, a, candidateList] = await Promise.all([
    api<{ items: Job[] }>("/jobs/mine"),
    api<Analytics>("/analytics"),
    api<CandidateProfile[]>("/candidates"),
  ]);
  analytics = a;
  if (pageRender !== renderId) return;

  const topCandidates = candidateList.slice(0, 4);
  const avgFit =
    a.average_score ||
    (candidateList.length
      ? candidateList.reduce((sum, c) => sum + (c.match_score || 0), 0) /
        candidateList.length
      : 80);

  shell(
    `${heading(
      "GOOD TEAMS START WITH GREAT CONNECTIONS.",
      "Find your next great hire.",
      "Connect with candidates whose verified skills fit your ambition.",
      `<a class="btn btn-primary" href="#/post-job">${icon("plus")} Post a job</a>`,
    )}${recruiterStats(data.items.length, candidateList.length, a.applications, avgFit)}${sectionTitle(
      "Your opportunities",
      "Manage your active job postings and applicants.",
      `<a class="text-link" href="#/post-job">Post new role ${icon("arrow-right")}</a>`,
    )}<div class="all-jobs-grid">${
      data.items
        .map(
          (j) =>
            `<div class="panel managed-job"><h3>${e(j.title)}</h3><p>${e(j.company)} · ${e(j.location)}</p><div class="strength-chips">${j.skills
              .slice(0, 4)
              .map((s) => chip(s))
              .join(
                "",
              )}</div><div class="manage-actions"><a class="text-link" href="#/candidates">Ranked candidates</a><a href="#/post-job/${j.id}" class="text-link">Edit ${icon("pencil")}</a><button class="text-link danger delete-job" data-id="${j.id}">Close role ${icon("x")}</button></div></div>`,
        )
        .join("") ||
      empty(
        "Your next teammate is out there.",
        "Post a role to start connecting with verified candidates.",
        "Post your first job",
        "post-job",
      )
    }</div>${sectionTitle(
      "Top matched talent pool",
      "High-fit candidates automatically scored for your open positions.",
      `<a class="text-link" href="#/candidates">Explore all candidates (${candidateList.length}) ${icon("arrow-right")}</a>`,
    )}<div class="candidates-preview-grid">${
      topCandidates
        .map(
          (c) =>
            `<div class="panel candidate-card"><div class="candidate-header"><div class="avatar">${e(initials(c.name))}</div><div><strong>${e(c.name)}</strong><span>${e(c.headline || "Candidate")}</span></div><span class="match-pill">${icon("sparkles")} ${c.match_score ? Math.round(c.match_score) + "% match" : "Verified"}</span></div><p class="candidate-snippet">${e(c.snippet)}</p><div class="candidate-meta"><span class="experience-badge">${icon("clock-3")} ${c.experience_years}y exp</span><div class="strength-chips">${c.skills.slice(0, 3).map((s) => chip(s)).join("")}${c.skills.length > 3 ? chip("+" + (c.skills.length - 3)) : ""}</div></div><div class="candidate-footer"><button class="btn btn-outline btn-sm view-candidate-btn" data-id="${c.id}">View resume</button><a class="btn btn-primary btn-sm" href="mailto:${e(c.email)}?subject=Opportunity%20via%20SkillMatch">Contact ${icon("arrow-up-right")}</a></div></div>`,
        )
        .join("")
    }</div>`,
    "Recruiter overview",
  );
}
async function postJob(id?: number): Promise<void> {
  const pageRender = renderId;
  if (!user) {
    authPage();
    return;
  }
  const job = id ? await api<Job>(`/jobs/${id}`) : null;
  if (pageRender !== renderId) return;
  shell(
    `${heading("MAKE ROOM FOR GREAT PEOPLE.", job ? "Refine your opportunity." : "A great role deserves a great match.", "Tell candidates what they’ll build, learn, and bring to your team.")}<form id="post-job-form" class="panel job-form" data-id="${id || ""}"><div class="row g-4">${[
      ["title", "Job title", "Senior Frontend Developer"],
      ["company", "Company", "Your company"],
      ["location", "Location", "Remote"],
    ]
      .map(
        ([k, l, p]) =>
          `<div class="col-md-6"><label for="${k}">${l}</label><input id="${k}" name="${k}" required maxlength="100" value="${e(job?.[k as keyof Job] || "")}" placeholder="${p}"></div>`,
      )
      .join(
        "",
      )}<div class="col-md-6"><label for="employment_type">Employment type</label><select id="employment_type" name="employment_type">${["Full-time", "Part-time", "Contract", "Internship"].map((t) => `<option ${job?.employment_type === t ? "selected" : ""}>${t}</option>`).join("")}</select></div><div class="col-md-6" style="display:flex;align-items:center;gap:10px;padding-top:28px"><input type="checkbox" id="remote" name="remote" ${job?.remote ? "checked" : ""} style="width:18px;height:18px;cursor:pointer"><label for="remote" style="margin:0;cursor:pointer;font-weight:600">Remote-friendly position</label></div><div class="col-md-6"><label for="salary_min">Minimum salary (optional)</label><input id="salary_min" name="salary_min" type="number" min="0" max="10000000" value="${job?.salary_min || ""}" placeholder="120000"></div><div class="col-md-6"><label for="salary_max">Maximum salary (optional)</label><input id="salary_max" name="salary_max" type="number" min="0" max="10000000" value="${job?.salary_max || ""}" placeholder="160000"></div><div class="col-md-6"><label for="salary_currency">Salary currency</label><input id="salary_currency" name="salary_currency" maxlength="3" pattern="[A-Z]{3}" placeholder="USD, INR, EUR" value="${e(job?.salary_currency || "")}"></div><div class="col-md-6"><label for="salary_interval">Pay period</label><select id="salary_interval" name="salary_interval"><option value="">Not specified</option>${["year", "month", "hour"].map((v) => `<option value="${v}" ${job?.salary_interval === v ? "selected" : ""}>${v}</option>`).join("")}</select></div><div class="col-12"><label for="skills">Required skills</label><input id="skills" name="skills" required value="${e(job?.skills.join(", ") || "")}" placeholder="React, TypeScript, CSS"><small>Separate each skill with a comma. Up to 30 skills.</small></div><div class="col-12"><label for="description">About the opportunity</label><textarea id="description" name="description" required minlength="40" maxlength="20000" rows="8" placeholder="Describe the work, the team, and what success looks like…">${e(job?.description || "")}</textarea></div></div><div class="form-error" role="alert"></div><button class="btn btn-primary" type="submit">${job ? "Save changes" : "Publish opportunity"} ${icon("arrow-up-right")}</button></form>`,
    job ? "Edit job" : "Post a job",
  );
}
async function adminPage(): Promise<void> {
  const pageRender = renderId;
  if (!user || user.role !== "admin") {
    if (pageRender !== renderId) return;
    shell(
      empty(
        "This space is for administrators.",
        "Sign in with an administrator account to manage the platform.",
        "Sign in",
        "login",
      ),
      "Administration",
    );
    return;
  }
  const page =
    Number(new URLSearchParams(location.hash.split("?")[1]).get("page")) || 1;
  const data = await api<{
    stats: Record<string, number>;
    users: User[];
    jobs: Job[];
  }>(`/admin?page=${page}`);
  if (pageRender !== renderId) return;
  shell(
    `${heading("THE BIGGER PICTURE.", "Platform overview.", "Manage accounts and keep the opportunity catalog healthy.")}<div class="stats-grid">${Object.entries(
      data.stats,
    )
      .map(
        ([k, v]) =>
          `<div class="stat-card"><span>${e(k)}</span><div class="stat-value">${v}</div></div>`,
      )
      .join(
        "",
      )}</div><div class="panel" style="margin-bottom:20px;padding:20px;background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.08);border-radius:12px"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px"><div><h3 style="margin:0 0 6px 0;font-size:16px">Vector Index & Embeddings</h3><p style="margin:0;font-size:13px;color:rgba(255,255,255,0.6)">Recompute all job, resume and chunk vectors using the active model (Ollama all-minilm:l6, 384 dims).</p></div><button class="btn btn-primary" id="btn-admin-reembed" style="font-size:12px;padding:8px 16px">Re-embed everything</button></div></div><div class="panel table-panel"><h2>People on the platform</h2><div class="table-responsive"><table class="app-table"><thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Account</th></tr></thead><tbody>${data.users.map((u) => `<tr><td>${e(u.name)}</td><td>${e(u.email)}</td><td>${u.role}</td><td><button class="btn btn-outline toggle-user" data-id="${u.id}" data-active="${u.active}" ${u.id === user?.id ? "disabled" : ""}>${u.active ? "Disable" : "Enable"}</button></td></tr>`).join("")}</tbody></table></div></div><div class="panel table-panel admin-jobs"><h2>Active job postings</h2><div class="table-responsive"><table class="app-table"><thead><tr><th>Role</th><th>Company</th><th>Manage</th></tr></thead><tbody>${data.jobs.map((j) => `<tr><td>${e(j.title)}</td><td>${e(j.company)}</td><td><button class="text-link danger delete-job" data-id="${j.id}">Close role</button></td></tr>`).join("")}</tbody></table></div></div><div class="pagination-controls"><a class="btn btn-outline" href="#/admin?page=${Math.max(1, page - 1)}">Previous</a><span>Page ${page}</span><a class="btn btn-outline" href="#/admin?page=${page + 1}">Next</a></div>`,
    "Administration",
  );
}
function notFound(): void {
  shell(
    `<div class="not-found"><span>404</span><h1>A little off the path.</h1><p>This page isn’t here. Your next opportunity still is.</p><a class="btn btn-primary" href="#/dashboard">Back to your workspace ${icon("arrow-right")}</a></div>`,
    "Page not found",
  );
}
async function navigate(): Promise<void> {
  renderId++;
  const navigationId = renderId;
  stopWorkspace();
  jobObserver?.disconnect();
  cleanupScene?.();
  cleanupCharts?.();
  ScrollTrigger.getAll().forEach((t) => t.kill());
  $("body").removeClass("nav-open");
  selectedFile = null;
  const path = route().split("?")[0];
  window.scrollTo(0, 0);
  try {
    if (path === "landing") {
      landing();
      return;
    }
    if (path === "login" || path === "register") {
      authPage(path === "register");
      return;
    }
    if (
      !user &&
      !["jobs", "analytics"].includes(path) &&
      !/^jobs\/\d+$/.test(path)
    ) {
      authPage();
      return;
    }
    if (
      user &&
      user?.role !== "candidate" &&
      ["dashboard", "upload", "matches", "settings", "learning", "saved-searches"].includes(path)
    ) {
      await recruiterPage();
      return;
    }
    $("dialog.workspace-dialog").remove();
    document.body.classList.remove("modal-open");
    shell(`<div class="skeleton" aria-label="Loading page"></div>`, "Loading");
    if (await workspaceRoute(path)) return;
    if (path === "dashboard") {
      const activeRender = renderId;
      await loadCandidate();
      if (activeRender !== renderId) return;
      dashboard();
    } else if (path === "upload") {
      resumes = await api<Resume[]>("/resumes");
      if (navigationId !== renderId) return;
      uploadPage();
    } else if (path === "jobs") await jobsPage();
    else if (/^jobs\/\d+$/.test(path))
      await jobDetail(Number(path.split("/")[1]));
    else if (path === "matches") await matchesPage();
    else if (/^matches\/\d+$/.test(path)) {
      const id = Number(path.split("/")[1]);
      await jobDetail(id);
    } else if (path === "analytics") await analyticsPage();
    else if (path === "applications" || path === "candidates") await applicationsPage();
    else if (path === "recruiter") await recruiterPage();
    else if (path.startsWith("post-job"))
      await postJob(Number(path.split("/")[1]) || undefined);
    else if (path === "admin") await adminPage();
    else if (path === "assistant") await assistantPage();
    else notFound();
  } catch (err) {
    if (navigationId !== renderId) return;
    shell(
      empty(
        "Let’s try that again.",
        e((err as Error).message),
        "Back to overview",
        "dashboard",
      ),
      "Something went wrong",
    );
    toast((err as Error).message, "error");
  }
}
async function busy(
  button: JQuery,
  action: () => Promise<void>,
): Promise<void> {
  const old = button.html();
  button
    .prop("disabled", true)
    .html('<span class="button-spinner"></span> Working…');
  try {
    await action();
  } catch (err) {
    toast((err as Error).message, "error");
    button
      .closest("form")
      .find(".form-error")
      .text((err as Error).message);
  } finally {
    button.prop("disabled", false).html(old);
    createIcons({ icons });
  }
}
function requireAccount(): boolean {
  if (!user) {
    toast("Create an account to use your own resume and apply for live roles.");
    location.hash = "/register";
    return false;
  }
  return true;
}
async function latestResume(): Promise<Resume> {
  resumes = await api<Resume[]>("/resumes");
  if (!resumes.length) {
    location.hash = "/upload";
    throw new Error("Upload a resume first so we can understand your skills.");
  }
  return resumes[0];
}
function selectFile(file: File): void {
  const error = validateFile(file);
  if (error) {
    toast(error, "error");
    selectedFile = null;
    $("#selected-file").empty();
    return;
  }
  selectedFile = file;
  $("#selected-file").html(
    `<div class="selected-file">${icon("file-check")}<span>${e(file.name)}<small>${(file.size / 1024).toFixed(0)} KB · Ready to analyze</small></span><button type="button" class="icon-btn clear-file" aria-label="Remove selected file">${icon("x")}</button></div>`,
  );
  createIcons({ icons });
}
$(document).on("click", ".menu-toggle,.sidebar-scrim", () =>
  $("body").toggleClass("nav-open"),
);
$(document).on("click", ".sidebar nav a", () =>
  $("body").removeClass("nav-open"),
);
$(document).on("click", "#account-button", function () {
  if (!user) {
    location.hash = "/login";
    return;
  }
  void busy($(this), async () => {
    await api("/auth/logout", "POST");
    setToken("");
    localStorage.removeItem("sm-session");
    user = null;
    clearWorkspace();
    location.hash = "/login";
  });
});
$(document).on("click", ".save-job", function () {
  if (!requireAccount()) return;
  void busy($(this), async () => {
    await api(`/jobs/${Number($(this).data("id"))}/save`, "POST");
    $(this).addClass("saved").attr("aria-pressed", "true");
    toast("Saved in your application tracker.");
  });
});
$(document).on("submit", "#job-search", function (ev) {
  ev.preventDefault();
  void busy($(this).find("button"), () => searchJobs());
});
$(document).on("click", ".retry-jobs", () => {
  void searchJobs().catch((err) => toast(err.message, "error"));
});
$(document).on("click", ".load-more-jobs", function () {
  void busy($(this), () => searchJobs(true));
});
$(document).on("click", "#btn-admin-reembed", function () {
  const btn = $(this);
  void busy(btn, async () => {
    const res = await api<{
      status: string;
      jobs_embedded: number;
      resumes_embedded: number;
      matches_reindexed: number;
    }>("/admin/re-embed", "POST");
    toast(
      `Re-embedding complete: ${res.jobs_embedded} jobs, ${res.resumes_embedded} resumes embedded, ${res.matches_reindexed} matches reindexed.`,
    );
    await adminPage();
  });
});
$(document).on("change", "#resume-file", function () {
  const file = (this as HTMLInputElement).files?.[0];
  if (file) selectFile(file);
});
$(document).on("keydown", ".dropzone", function (ev) {
  if (ev.key === "Enter" || ev.key === " ") {
    ev.preventDefault();
    $("#resume-file").trigger("click");
  }
});
$(document).on("dragover", ".dropzone", function (ev) {
  ev.preventDefault();
  $(this).addClass("dragging");
});
$(document).on("dragleave", ".dropzone", function () {
  $(this).removeClass("dragging");
});
$(document).on("drop", ".dropzone", function (ev) {
  ev.preventDefault();
  $(this).removeClass("dragging");
  const file = (ev.originalEvent as DragEvent).dataTransfer?.files[0];
  if (file) selectFile(file);
});
$(document).on("click", ".clear-file", () => {
  selectedFile = null;
  $("#resume-file").val("");
  $("#selected-file").empty();
});
$(document).on("submit", "#upload-form", function (ev) {
  ev.preventDefault();
  if (!selectedFile) {
    $(this).find(".form-error").text("Choose a PDF or DOCX resume first.");
    return;
  }
  if (!requireAccount()) return;
  const data = new FormData();
  data.append("file", selectedFile);
  void busy($(this).find("[type=submit]"), async () => {
    const resume = await api<Resume>("/resumes", "POST", data);
    resumes.unshift(resume);
    toast(
      `Resume saved. We found ${resume.skills.length} skills and updated available job matches.`,
    );
    location.hash = "/dashboard";
  });
});
$(document).on("click", ".load-more-matches", function () {
  const button = $(this);
  const page = Number(button.data("page"));
  const activeRender = renderId;
  void busy(button, async () => {
    const next = await api<Match[]>(`/matches?page=${page}&size=12`);
    if (activeRender !== renderId || route() !== "matches") return;
    matches.push(...next);
    $("#match-results").append(
      next.map((m) => jobCard({ ...m.job, score: m.score })).join(""),
    );
    if (next.length < 12) button.remove();
    else button.data("page", page + 1);
    finish();
  });
});
$(document).on("click", ".delete-resume", function () {
  const id = $(this).data("id");
  void busy($(this), async () => {
    await api(`/resumes/${id}`, "DELETE");
    toast("Resume and related analyses deleted.");
    await navigate();
  });
});
$(document).on("click", ".set-primary-resume", function () {
  const id = $(this).data("id");
  void busy($(this), async () => {
    await api(`/resumes/${id}/primary`, "PATCH");
    toast("Primary resume updated. Matching and scores refreshed.");
    await navigate();
  });
});
$(document).on("submit", "#auth-form", function (ev) {
  ev.preventDefault();
  const form = $(this);
  if (!(this as HTMLFormElement).reportValidity()) return;
  const payload = Object.fromEntries(
    form.serializeArray().map((x) => [x.name, x.value]),
  );
  void busy(form.find("[type=submit]"), async () => {
    const data = await api<{ access_token: string; user: User }>(
      `/auth/${form.data("mode")}`,
      "POST",
      payload,
    );
    setToken(data.access_token);
    user = data.user;
    await loadPreferences();
    startNotifications();
    localStorage.setItem("sm-session", "active");
    toast(
      `Welcome${form.data("mode") === "login" ? " back" : ""}, ${user.name.split(" ")[0]}.`,
    );
    location.hash =
      user.role === "admin"
        ? "/admin"
        : user.role === "recruiter"
          ? "/recruiter"
          : "/dashboard";
  });
});
$(document).on("click", ".toggle-password", function () {
  const input = $("#password");
  const show = input.attr("type") === "password";
  input.attr("type", show ? "text" : "password");
  $(this).attr("aria-label", show ? "Hide password" : "Show password");
});
$(document).on("click", ".analyze-job", function () {
  const id = Number($(this).data("id"));
  void busy($(this), async () => {
    if (!requireAccount()) return;
    const resume = await latestResume();
    await api<Match>("/matches", "POST", { job_id: id, resume_id: resume.id });
    location.hash = `/matches/${id}`;
  });
});
$(document).on("click", ".apply-job", function () {
  if (!requireAccount()) return;
  const id = Number($(this).data("id"));
  void busy($(this), async () => {
    const resume = await latestResume();
    await api("/applications", "POST", { job_id: id, resume_id: resume.id });
    toast("You’ve made your move. Application recorded.");
    location.hash = "/applications";
  });
});
$(document).on("submit", "#post-job-form", function (ev) {
  ev.preventDefault();
  const form = $(this);
  if (!(this as HTMLFormElement).reportValidity()) return;
  const data: Record<string, unknown> = Object.fromEntries(
    form.serializeArray().map((x) => [x.name, x.value]),
  );
  data.skills = String(data.skills)
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  data.salary_min = data.salary_min === "" ? null : Number(data.salary_min);
  data.salary_max = data.salary_max === "" ? null : Number(data.salary_max);
  data.salary_currency = data.salary_currency || null;
  data.salary_interval = data.salary_interval || null;
  data.remote = form.find("#remote").is(":checked");
  if (
    data.salary_min != null &&
    data.salary_max != null &&
    Number(data.salary_max) < Number(data.salary_min)
  ) {
    form
      .find(".form-error")
      .text("Maximum salary must be at least the minimum.");
    return;
  }
  void busy(form.find("[type=submit]"), async () => {
    await api(
      form.data("id") ? `/jobs/${form.data("id")}` : "/jobs",
      form.data("id") ? "PUT" : "POST",
      data,
    );
    toast("Your opportunity is active and scored against candidates.");
    location.hash = "/recruiter";
  });
});
$(document).on("click", ".delete-job", function () {
  const id = $(this).data("id");
  void busy($(this), async () => {
    await api(`/jobs/${id}`, "DELETE");
    toast("Role closed. Existing applications are retained.");
    await navigate();
  });
});
$(document).on("change", ".status-select", function () {
  const el = $(this);
  void api(`/applications/${el.data("id")}`, "PATCH", { status: el.val() })
    .then(() => toast("Application status updated."))
    .catch((err) => {
      toast(err.message, "error");
      void navigate();
    });
});
$(document).on("click", ".candidate-tab-btn", function () {
  $(".candidate-tab-btn").removeClass("active");
  $(this).addClass("active");
  const tab = $(this).data("tab") as "pool" | "applicants";
  activeCandidateTab = tab;
  if (tab === "pool") {
    $("#talent-pool-view").show();
    $("#direct-applicants-view").hide();
  } else {
    $("#talent-pool-view").hide();
    $("#direct-applicants-view").show();
  }
});
$(document).on("input", "#candidate-search", function () {
  candidateSearchQuery = $(this).val() as string;
  $("#candidates-pool-cards").html(renderTalentPool());
  createIcons({ icons });
});
$(document).on("click", ".skill-filter-pill", function () {
  const skill = ($(this).data("skill") || "") as string;
  candidateFilterSkill = skill.toLowerCase() === candidateFilterSkill.toLowerCase() ? "" : skill;
  $(".skill-filter-pill").removeClass("active");
  if (candidateFilterSkill) {
    $(this).addClass("active");
  } else {
    $(`.skill-filter-pill[data-skill=""]`).addClass("active");
  }
  $("#candidates-pool-cards").html(renderTalentPool());
  createIcons({ icons });
});
$(document).on("click", "#btn-clear-cand-filters", function () {
  candidateFilterSkill = "";
  candidateSearchQuery = "";
  $("#candidate-search").val("");
  $(".skill-filter-pill").removeClass("active");
  $(`.skill-filter-pill[data-skill=""]`).addClass("active");
  $("#candidates-pool-cards").html(renderTalentPool());
  createIcons({ icons });
});
$(document).on("click", ".view-candidate-btn", function () {
  const id = Number($(this).data("id"));
  const cand = cachedCandidates.find((c) => c.id === id);
  if (!cand) return;
  const dialog = document.createElement("dialog");
  dialog.className = "candidate-dialog";
  dialog.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px">
      <div style="display:flex;align-items:center;gap:14px">
        <div class="avatar" style="width:48px;height:48px;font-size:18px">${e(initials(cand.name))}</div>
        <div>
          <h2 style="margin:0 0 4px 0;font-size:20px">${e(cand.name)}</h2>
          <span style="color:var(--muted);font-size:14px">${e(cand.headline)} · ${e(cand.email)}</span>
        </div>
      </div>
      <button class="icon-btn close-dialog-btn" aria-label="Close dialog">${icon("x")}</button>
    </div>
    <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;margin-bottom:18px">
      <span class="experience-badge">${icon("clock-3")} ${cand.experience_years} years experience</span>
      <span class="match-pill">${icon("sparkles")} ${cand.match_score ? Math.round(cand.match_score) + "% match score" : "Verified candidate"}</span>
      <span class="subtle" style="font-size:13px">Resume file: ${e(cand.resume_filename)}</span>
    </div>
    <div style="margin-bottom:20px">
      <strong style="display:block;margin-bottom:8px;font-size:13px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted)">Verified Skills</strong>
      <div class="strength-chips">${cand.skills.map((s) => chip(s)).join("")}</div>
    </div>
    <div style="margin-bottom:24px">
      <strong style="display:block;margin-bottom:8px;font-size:13px;text-transform:uppercase;letter-spacing:0.05em;color:var(--muted)">Parsed Resume Content</strong>
      <pre>${e(cand.resume_text)}</pre>
    </div>
    <div style="display:flex;justify-content:flex-end;gap:12px">
      <button class="btn btn-outline close-dialog-btn">Close</button>
      <a class="btn btn-primary" href="mailto:${e(cand.email)}?subject=Opportunity%20via%20SkillMatch">Contact Candidate ${icon("arrow-up-right")}</a>
    </div>
  `;
  document.body.appendChild(dialog);
  dialog.showModal();
  $(dialog).find(".close-dialog-btn").on("click", () => {
    dialog.close();
    dialog.remove();
  });
  createIcons({ icons });
});
$(document).on("click", ".toggle-user", function () {
  const el = $(this);
  void busy(el, async () => {
    await api(`/admin/users/${el.data("id")}`, "PATCH", {
      active: !el.data("active"),
    });
    toast("Account updated.");
    await navigate();
  });
});

// --- Career Assistant Full-Page View (No Modal) ---

function renderAssistantMarkdown(raw: string): string {
  if (!raw) return "";

  // 1. Extract code blocks first to protect from formatting
  const codeBlocks: string[] = [];
  let text = raw.replace(/```([a-zA-Z0-9_\-#\+\.]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    const cleanLang = (lang || "code").trim();
    const cleanCode = code.trim();
    const safeCode = e(cleanCode);
    codeBlocks.push(
      `<div class="assistant-code-block">` +
        `<div class="assistant-code-header">` +
          `<span>${e(cleanLang)}</span>` +
          `<button type="button" class="copy-code-btn" data-code="${e(cleanCode)}">Copy</button>` +
        `</div>` +
        `<pre><code>${safeCode}</code></pre>` +
      `</div>`
    );
    return `__CODE_BLOCK_${idx}__`;
  });

  // 2. Escape HTML for safety
  text = e(text);

  // 3. Inline code
  text = text.replace(/`([^`]+)`/g, "<code>$1</code>");

  // 4. Bold and Italic
  text = text.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  text = text.replace(/\*([^*]+)\*/g, "<em>$1</em>");

  // 5. Job citations [Job #123] and Resume citations [Resume: Experience]
  text = text.replace(/\[Job #(\d+)\]/g, '<button type="button" class="job-citation-chip" data-id="$1">💼 Job #$1 ↗</button>');
  text = text.replace(/\[Resume:\s*([^\]]+)\]/g, '<span class="resume-citation-chip">📄 $1</span>');

  // 6. Markdown links [text](url) -> new tab
  text = text.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="assistant-link">$1 ↗</a>');

  // 7. Structured lists and headings
  const lines = text.split("\n");
  const processedLines: string[] = [];
  let inList = false;

  for (const line of lines) {
    const listMatch = line.match(/^(\s*)[-*•]\s+(.*)$/);
    const numListMatch = line.match(/^(\s*)\d+\.\s+(.*)$/);
    if (listMatch) {
      if (!inList) {
        processedLines.push("<ul>");
        inList = true;
      }
      processedLines.push(`<li>${listMatch[2]}</li>`);
    } else if (numListMatch) {
      if (!inList) {
        processedLines.push("<ol>");
        inList = true;
      }
      processedLines.push(`<li>${numListMatch[2]}</li>`);
    } else {
      if (inList) {
        processedLines.push("</ul>");
        inList = false;
      }
      if (line.trim().startsWith("### ")) {
        processedLines.push(`<h4 style="margin: 12px 0 6px; font-size: 14px; font-weight: 700;">${line.replace(/^###\s+/, "")}</h4>`);
      } else if (line.trim().length > 0) {
        processedLines.push(`<p>${line}</p>`);
      }
    }
  }
  if (inList) processedLines.push("</ul>");
  text = processedLines.join("\n");

  // 8. Restore code blocks
  text = text.replace(/__CODE_BLOCK_(\d+)__/g, (_, idx) => codeBlocks[Number(idx)] || "");

  return text;
}

function renderAssistantJobCards(jobs: any[]): string {
  if (!jobs || !jobs.length) return "";
  return jobs.map(j => `
    <div class="assistant-job-card">
      <div class="assistant-job-header">
        <span class="assistant-job-title">${e(j.title)}</span>
        ${j.match_score ? `<span class="assistant-match-pill">${j.match_score}% Match</span>` : ""}
      </div>
      <div class="assistant-job-meta">
        <span>🏢 ${e(j.company)}</span>
        <span>📍 ${e(j.location || "Remote")}</span>
        ${j.salary && j.salary !== "Undisclosed" ? `<span>💰 ${e(j.salary)}</span>` : ""}
        ${j.experience_level ? `<span>🎓 ${e(j.experience_level)}</span>` : ""}
      </div>
      ${j.missing_skills && j.missing_skills.length ? `<div style="font-size:11px;color:var(--text-muted,#8b8a99)">Top missing: ${e(j.missing_skills.join(", "))}</div>` : ""}
      <div class="assistant-job-actions">
        <button type="button" class="btn btn-outline btn-sm job-open-btn" data-id="${j.job_id}" style="font-size:11px;padding:2px 8px">Open Job ↗</button>
        <button type="button" class="btn btn-primary btn-sm job-save-tracker-btn" data-id="${j.job_id}" style="font-size:11px;padding:2px 8px">Save to Tracker</button>
      </div>
    </div>
  `).join("");
}

function renderAssistantContextPanel(ctx: any): string {
  const resumeInfo = ctx.has_resume ? `
    <div class="assistant-context-section">
      <div class="assistant-context-header">Candidate Profile</div>
      <div class="assistant-context-card">
        <div style="font-weight: 600; font-size: 13px;">${e(ctx.candidate_name)}</div>
        <div style="font-size: 11.5px; color: var(--text-muted, #8b8a99);">
          📄 ${e(ctx.resume_filename || "Active Resume")} • ${ctx.experience_years || 0} yrs exp
        </div>
        ${ctx.top_skills && ctx.top_skills.length ? `
          <div style="margin-top: 4px;">
            <div style="font-size: 11px; color: var(--text-muted, #71717a); margin-bottom: 4px;">Top Skills:</div>
            <div class="assistant-skill-tags">
              ${ctx.top_skills.map((s: string) => `<span class="assistant-skill-tag">${e(s)}</span>`).join("")}
            </div>
          </div>
        ` : ""}
      </div>
    </div>
  ` : `
    <div class="assistant-context-section">
      <div class="assistant-context-header">Resume Status</div>
      <div class="assistant-context-card" style="text-align: center; padding: 16px 12px;">
        <div style="font-size: 24px; margin-bottom: 6px;">📄</div>
        <div style="font-size: 12.5px; font-weight: 600;">No resume uploaded</div>
        <div style="font-size: 11px; color: var(--text-muted, #8b8a99); margin: 4px 0 10px;">Upload your resume to unlock match breakdowns and personalized advice.</div>
        <a href="#/upload" class="btn btn-primary btn-sm" style="font-size: 11px; padding: 4px 10px;">Upload Resume</a>
      </div>
    </div>
  `;

  const topMatches = ctx.top_matches && ctx.top_matches.length ? `
    <div class="assistant-context-section">
      <div class="assistant-context-header">Top Matches</div>
      <div class="assistant-context-card">
        ${ctx.top_matches.map((m: any) => `
          <div class="assistant-context-match-item">
            <a href="#/jobs/${m.job_id}" title="${e(m.title)} at ${e(m.company)}">
              <strong>#${m.job_id}</strong> ${e(m.title)}
            </a>
            <span class="assistant-match-pill" style="font-size: 10px; padding: 1px 5px;">${m.score}%</span>
          </div>
        `).join("")}
      </div>
    </div>
  ` : "";

  return `
    <aside class="assistant-context-panel" id="assistant-context-sidebar">
      ${resumeInfo}
      ${topMatches}
      <div class="assistant-context-section">
        <div class="assistant-context-header">Recent Activity</div>
        <div class="assistant-context-card" id="assistant-recent-activity">
          <div style="font-size: 11.5px; color: var(--text-muted, #8b8a99);">
            Ready to assist with search, roadmaps, and match breakdowns.
          </div>
        </div>
      </div>
      <div class="assistant-context-section" style="margin-top: auto;">
        <button type="button" class="btn btn-outline btn-sm" id="btn-clear-chat-session" style="width: 100%; font-size: 12px; gap: 6px; display: inline-flex; align-items: center; justify-content: center;">
          ${icon("trash-2")} Clear Chat History
        </button>
      </div>
    </aside>
  `;
}

function renderAssistantEmptyState(ctx: any): string {
  const firstName = (ctx.candidate_name || "there").split(" ")[0];
  const prompts = ctx.suggested_prompts || [
    "Search remote Python internships",
    "How do I learn Docker?",
    "Explain my match for job #1",
    "Review my resume strengths",
  ];

  const iconsList = ["search", "sparkles", "briefcase-business", "book-open"];

  return `
    <div class="assistant-empty-state" id="assistant-empty-state">
      <div class="assistant-empty-icon">${icon("sparkles")}</div>
      <h2>Hello, ${e(firstName)}!</h2>
      <p>I'm your SkillMatch Career Assistant. Ask me anything about finding jobs, reviewing your resume match, or closing skill gaps.</p>
      <div class="assistant-suggestions-grid">
        ${prompts.map((p: string, idx: number) => `
          <button type="button" class="assistant-suggestion-card" data-prompt="${e(p)}">
            <div class="assistant-suggestion-header">
              <span>${icon(iconsList[idx % iconsList.length])}</span>
              <span>Suggestion ${idx + 1}</span>
            </div>
            <div class="assistant-suggestion-prompt">${e(p)}</div>
          </button>
        `).join("")}
      </div>
    </div>
  `;
}

function renderHistoryMessage(m: any): string {
  const isUser = m.role === "user";
  if (isUser) {
    return `
      <div class="assistant-message user">
        <div class="assistant-bubble-container">
          <div class="assistant-bubble user">${e(m.content)}</div>
          <div class="assistant-message-meta">
            <span>You</span>
          </div>
        </div>
        <div class="assistant-avatar user">${icon("file-user")}</div>
      </div>
    `;
  } else {
    const formattedContent = renderAssistantMarkdown(m.content);
    let jobCardsHtml = "";
    if (m.tool_calls && Array.isArray(m.tool_calls)) {
      for (const tc of m.tool_calls) {
        if (tc.tool === "search_jobs" && tc.result?.jobs) {
          jobCardsHtml += renderAssistantJobCards(tc.result.jobs);
        }
      }
    }
    return `
      <div class="assistant-message bot">
        <div class="assistant-avatar bot">✨</div>
        <div class="assistant-bubble-container">
          <div class="assistant-bubble bot">
            ${formattedContent}
            ${jobCardsHtml}
          </div>
          <div class="assistant-message-meta">
            <span>SkillMatch AI</span>
            <button type="button" class="assistant-meta-btn assistant-copy-msg-btn" title="Copy message">${icon("bookmark")} Copy</button>
            <button type="button" class="assistant-meta-btn assistant-retry-btn" title="Retry prompt">${icon("route")} Retry</button>
          </div>
        </div>
      </div>
    `;
  }
}

async function assistantPage(): Promise<void> {
  const pageRender = renderId;
  $("dialog.workspace-dialog").remove();
  document.body.classList.remove("modal-open");

  if (!resumes.length && user?.role === "candidate") {
    try {
      resumes = await api<Resume[]>("/resumes");
    } catch {}
  }

  let ctx: any = {
    candidate_name: user?.name || "Candidate",
    has_resume: resumes.length > 0,
    resume_filename: resumes[0]?.filename || null,
    experience_years: resumes[0]?.experience_years || 0,
    top_skills: resumes[0]?.skills?.slice(0, 6) || [],
    suggested_prompts: [],
  };
  let history: any[] = [];
  try {
    const [ctxData, histData] = await Promise.all([
      api<any>("/ai/assistant/context"),
      api<{ items: any[] }>("/ai/chat/history"),
    ]);
    if (pageRender !== renderId) return;
    if (ctxData) {
      ctx = { ...ctx, ...ctxData };
      if (!ctx.has_resume && resumes.length > 0) {
        ctx.has_resume = true;
        ctx.resume_filename = ctx.resume_filename || resumes[0]?.filename;
        ctx.experience_years = ctx.experience_years || resumes[0]?.experience_years || 0;
        ctx.top_skills = (ctx.top_skills && ctx.top_skills.length) ? ctx.top_skills : (resumes[0]?.skills || []).slice(0, 6);
      }
    }
    history = histData?.items || [];
  } catch (err) {
    console.error("Failed to load assistant context", err);
    if (!ctx.has_resume && resumes.length > 0) {
      ctx.has_resume = true;
      ctx.resume_filename = resumes[0]?.filename;
      ctx.experience_years = resumes[0]?.experience_years || 0;
      ctx.top_skills = (resumes[0]?.skills || []).slice(0, 6);
    }
  }

  const hasHistory = history.length > 0;

  const content = `
    <div class="assistant-page-container">
      <div class="assistant-chat-column">
        <div class="assistant-chat-header">
          <div class="assistant-header-title">
            <h1>SkillMatch Career Assistant</h1>
            <span class="assistant-header-badge">${icon("sparkles")} Grounded RAG</span>
          </div>
          <div class="assistant-header-actions">
            <button type="button" class="btn btn-outline btn-sm" id="btn-new-chat" style="font-size: 11.5px; padding: 4px 10px; display: inline-flex; align-items: center; gap: 5px;">
              ${icon("plus")} New Chat
            </button>
          </div>
        </div>

        <div class="assistant-messages-scroll" id="assistant-messages-container">
          <div class="assistant-messages-inner" id="assistant-messages-list">
            ${!hasHistory ? renderAssistantEmptyState(ctx) : ""}
            ${history.map(m => renderHistoryMessage(m)).join("")}
          </div>
        </div>

        <div class="assistant-composer-area">
          <div class="assistant-composer-wrapper">
            <textarea
              id="assistant-textarea"
              class="assistant-textarea"
              placeholder="Ask about jobs, matches, skills, or roadmaps... (Enter to send, Shift+Enter for newline)"
              rows="1"
            ></textarea>
            <div class="assistant-composer-footer">
              <span class="assistant-composer-hint">Shift+Enter for newline</span>
              <div class="assistant-composer-buttons">
                <button type="button" class="assistant-stop-btn" id="assistant-stop-btn" style="display: none;">
                  Stop
                </button>
                <button type="button" class="assistant-send-btn" id="assistant-send-btn" aria-label="Send message">
                  ${icon("send")}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      ${renderAssistantContextPanel(ctx)}
    </div>
  `;

  shell(content, "Career Assistant");
  createIcons({ icons });

  $("#assistant-textarea").trigger("focus");

  if (hasHistory) {
    const scrollEl = $("#assistant-messages-container");
    if (scrollEl.length) scrollEl.scrollTop(scrollEl[0].scrollHeight);
  }
}

let activeAiStreamStop: (() => void) | null = null;
let lastAssistantUserMsg = "";

async function sendAssistantMessage(): Promise<void> {
  const textarea = $("#assistant-textarea");
  const msg = String(textarea.val() || "").trim();
  if (!msg) return;

  lastAssistantUserMsg = msg;
  textarea.val("");
  textarea.css("height", "auto");

  $("#assistant-empty-state").remove();

  const list = $("#assistant-messages-list");

  list.append(`
    <div class="assistant-message user">
      <div class="assistant-bubble-container">
        <div class="assistant-bubble user">${e(msg)}</div>
        <div class="assistant-message-meta">
          <span>You</span>
        </div>
      </div>
      <div class="assistant-avatar user">${icon("file-user")}</div>
    </div>
  `);

  const botId = "assistant-bot-msg-" + Date.now();
  list.append(`
    <div class="assistant-message bot" id="${botId}">
      <div class="assistant-avatar bot">✨</div>
      <div class="assistant-bubble-container">
        <div class="assistant-tool-status-area"></div>
        <div class="assistant-bubble bot">
          <span class="typing-cursor">Thinking…</span>
        </div>
        <div class="assistant-message-meta" style="display: none;">
          <span>SkillMatch AI</span>
          <button type="button" class="assistant-meta-btn assistant-copy-msg-btn">${icon("bookmark")} Copy</button>
          <button type="button" class="assistant-meta-btn assistant-retry-btn">${icon("route")} Retry</button>
        </div>
      </div>
    </div>
  `);

  createIcons({ icons });

  const container = $("#assistant-messages-container");
  if (container.length) container.scrollTop(container[0].scrollHeight);

  const stopBtn = $("#assistant-stop-btn").show();
  const sendBtn = $("#assistant-send-btn").prop("disabled", true);

  const botMsgEl = $(`#${botId}`);
  const toolArea = botMsgEl.find(".assistant-tool-status-area");
  const bubble = botMsgEl.find(".assistant-bubble");
  let accumulatedText = "";
  let returnedJobs: any[] = [];

  activeAiStreamStop?.();
  activeAiStreamStop = aiChatStream(msg, (event: any) => {
    if (event.type === "tool") {
      const isErr = event.status === "error";
      const chipClass = isErr ? "error" : (event.status === "running" ? "running" : "done");
      const iconText = isErr ? "⚠️" : (event.status === "running" ? '<span class="tool-spinner"></span>' : "✓");
      const label = event.label || `Executing ${event.tool || "tool"}...`;

      toolArea.html(`
        <div class="assistant-tool-chip ${chipClass}">
          ${iconText} <span>${e(label)}</span>
        </div>
      `);

      $("#assistant-recent-activity").html(`
        <div style="font-size: 11.5px; color: var(--text, #d4d4d8); display: flex; align-items: center; gap: 6px;">
          ${iconText} <span>${e(label)}</span>
        </div>
      `);

      if (event.tools && event.tools.length) {
        const t = event.tools[0];
        if (t.result?.jobs) {
          returnedJobs = t.result.jobs;
        }
      }
    } else if (event.type === "token" && event.content) {
      accumulatedText += event.content;
      bubble.html(renderAssistantMarkdown(accumulatedText) + '<span class="typing-cursor">▌</span>');
      const el = container[0];
      if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 120) {
        container.scrollTop(el.scrollHeight);
      }
    } else if (event.type === "done") {
      stopBtn.hide();
      sendBtn.prop("disabled", false);
      activeAiStreamStop = null;

      let finalHtml = renderAssistantMarkdown(accumulatedText);
      if (returnedJobs && returnedJobs.length) {
        finalHtml += renderAssistantJobCards(returnedJobs);
      }
      if (event.provider && event.latency_ms) {
        finalHtml += `<div style="font-size:10.5px;color:var(--text-muted,#71717a);margin-top:8px;padding-top:4px;border-top:1px dashed rgba(255,255,255,0.08)">⚡ ${e(event.provider)} • ${event.latency_ms}ms</div>`;
      }
      bubble.html(finalHtml);
      botMsgEl.find(".assistant-message-meta").show();
      createIcons({ icons });

      const el = container[0];
      if (el && el.scrollHeight - el.scrollTop - el.clientHeight < 150) {
        container.scrollTop(el.scrollHeight);
      }
    } else if (event.type === "error") {
      stopBtn.hide();
      sendBtn.prop("disabled", false);
      activeAiStreamStop = null;
      bubble.html(`
        <div style="color: #fca5a5; font-size: 13px;">
          ⚠️ ${e(event.content || "The request timed out or encountered an error. Please try again.")}
        </div>
      `);
      botMsgEl.find(".assistant-message-meta").show();
      createIcons({ icons });
    }
  });
}

// Global Event Handlers for Career Assistant
$(document).on("click", ".ai-assistant-btn", function (e) {
  e.preventDefault();
  location.hash = "#/assistant";
});

$(document).on("keydown", function (e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    location.hash = "#/assistant";
  }
});

$(document).on("input", "#assistant-textarea", function () {
  this.style.height = "auto";
  this.style.height = Math.min(this.scrollHeight, 160) + "px";
});

$(document).on("keydown", "#assistant-textarea", function (e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    void sendAssistantMessage();
  }
});

$(document).on("click", "#assistant-send-btn", function () {
  void sendAssistantMessage();
});

$(document).on("click", "#assistant-stop-btn", function () {
  if (activeAiStreamStop) {
    activeAiStreamStop();
    activeAiStreamStop = null;
    $("#assistant-stop-btn").hide();
    $("#assistant-send-btn").prop("disabled", false);
    $(".typing-cursor").remove();
  }
});

$(document).on("click", ".assistant-retry-btn", function () {
  if (lastAssistantUserMsg) {
    $("#assistant-textarea").val(lastAssistantUserMsg);
    void sendAssistantMessage();
  }
});

$(document).on("click", ".assistant-copy-msg-btn", function () {
  const text = $(this).closest(".assistant-bubble-container").find(".assistant-bubble").text();
  navigator.clipboard.writeText(text);
  toast("Message copied to clipboard.");
});

$(document).on("click", ".copy-code-btn", function () {
  const code = String($(this).data("code") || "");
  navigator.clipboard.writeText(code);
  $(this).text("Copied!");
  setTimeout(() => $(this).text("Copy"), 2000);
});

$(document).on("click", ".job-citation-chip, .job-open-btn", function () {
  const id = Number($(this).data("id"));
  location.hash = `#/jobs/${id}`;
});

$(document).on("click", ".job-save-tracker-btn", async function () {
  const id = Number($(this).data("id"));
  const btn = $(this).prop("disabled", true).text("Saving…");
  try {
    await api("/applications", "POST", { job_id: id, status: "Saved" });
    toast("Saved to your Kanban tracker!");
    btn.text("Saved ✓");
  } catch (err) {
    toast((err as Error).message, "error");
    btn.prop("disabled", false).text("Save to Tracker");
  }
});

$(document).on("click", ".assistant-suggestion-card", function () {
  const prompt = String($(this).data("prompt") || "");
  if (prompt) {
    $("#assistant-textarea").val(prompt);
    void sendAssistantMessage();
  }
});

$(document).on("click", "#btn-new-chat, #btn-clear-chat-session", async function () {
  try {
    await api("/ai/chat/history", "DELETE");
    toast("New chat session started.");
    await assistantPage();
  } catch (err) {
    toast((err as Error).message, "error");
  }
});

$(document).on("click", "#btn-nl-search", async function () {
  const query = String($("#nl-search-input").val() || "").trim();
  if (!query) return;
  const btn = $(this).prop("disabled", true).text("Parsing…");
  try {
    const data = await api<{
      parsed_filters: {
        q?: string;
        country?: string;
        experience_level?: string;
        remote?: boolean;
        salary_disclosed?: boolean;
      };
      total: number;
    }>("/ai/nl-search", "POST", { query, limit: 12 });
    const f = data.parsed_filters;
    const form = $("#job-search");
    form.find("[name=q]").val(f.q || "");
    if (f.country) form.find("[name=country]").val(f.country);
    form.find("[name=experience_level]").val(f.experience_level || "");
    form.find("[name=remote]").prop("checked", Boolean(f.remote));
    form.find("[name=salary_disclosed]").prop("checked", Boolean(f.salary_disclosed));

    $("#ai-filters-applied")
      .removeAttr("hidden")
      .text(`✨ AI applied filters: Query: "${f.q || query}" • Country: ${f.country || "Any"} • Level: ${f.experience_level || "Any"} • Remote: ${f.remote ? "Yes" : "Any"}`);
    await searchJobs();
  } catch (err) {
    toast((err as Error).message, "error");
  } finally {
    btn.prop("disabled", false).text("Search with AI");
  }
});

$(document).on("click", ".remove-chip-btn", function () {
  const field = $(this).data("field");
  const form = $("#job-search");
  if (field === "q") form.find("[name=q]").val("");
  else if (field === "location") form.find("[name=location]").val("");
  else if (field === "country") form.find("[name=country]").val("India + Remote worldwide");
  else if (field === "experience_level") form.find("[name=experience_level]").val("");
  else if (field === "kind") form.find("[name=kind]").val("");
  else if (field === "remote") form.find("[name=remote]").prop("checked", false);
  else if (field === "salary_disclosed") form.find("[name=salary_disclosed]").prop("checked", false);
  else if (field === "days") form.find("[name=days]").val("");
  void searchJobs();
});

$(document).on("click", ".btn-remove-filter", function () {
  const field = $(this).data("field");
  const form = $("#job-search");
  if (field === "q") form.find("[name=q]").val("");
  else if (field === "location") form.find("[name=location]").val("");
  else if (field === "country") form.find("[name=country]").val("India + Remote worldwide");
  else if (field === "experience_level") form.find("[name=experience_level]").val("");
  else if (field === "remote") form.find("[name=remote]").prop("checked", false);
  else {
    form.find("[name=q]").val("");
    form.find("[name=location]").val("");
    form.find("[name=country]").val("India + Remote worldwide");
    form.find("[name=remote]").prop("checked", false);
  }
  void searchJobs();
});

$(document).on("click", ".btn-widen-worldwide", function () {
  const form = $("#job-search");
  form.find("[name=country]").val("");
  form.find("[name=remote]").prop("checked", true);
  void searchJobs();
});

$(document).on("click", ".btn-clear-all-filters", function () {
  const form = $("#job-search");
  form.find("[name=q]").val("");
  form.find("[name=location]").val("");
  form.find("[name=country]").val("India + Remote worldwide");
  form.find("[name=experience_level]").val("");
  form.find("[name=kind]").val("");
  form.find("[name=days]").val("");
  form.find("[name=remote]").prop("checked", false);
  form.find("[name=salary_disclosed]").prop("checked", false);
  form.find("[name=min_match]").val("0");
  $("#ai-filters-applied").attr("hidden", "true");
  void searchJobs();
});
$(document).on("keydown", "#nl-search-input", function (ev) {
  if (ev.key === "Enter") {
    ev.preventDefault();
    $("#btn-nl-search").trigger("click");
  }
});
$(document).on("click", ".scroll-link", function (ev) {
  ev.preventDefault();
  document
    .getElementById("how-it-works")
    ?.scrollIntoView({ behavior: reduced ? "instant" : "smooth" });
});
$(document).on("keydown", (ev) => {
  if (ev.key === "/" && !$(ev.target).is("input,textarea,select")) {
    ev.preventDefault();
    location.hash = "/jobs";
    setTimeout(() => $("[name=q]").trigger("focus"), 100);
  }
  if (ev.key === "Escape") $("body").removeClass("nav-open");
});
if (!reduced) {
  $(document).on("mousemove", ".magnetic", function (ev) {
    const rect = this.getBoundingClientRect();
    gsap.to(this, {
      x: (ev.clientX - rect.left - rect.width / 2) * 0.1,
      y: (ev.clientY - rect.top - rect.height / 2) * 0.15,
      duration: 0.3,
    });
  });
  $(document).on("mouseleave", ".magnetic", function () {
    gsap.to(this, { x: 0, y: 0, duration: 0.3 });
  });
}
let semanticDegradedMessage: string | null = null;
async function checkSystemHealth(): Promise<void> {
  try {
    const health = await api<{ status: string; semantic_search: string; semantic_message?: string }>("/health");
    if (health.semantic_search === "degraded") {
      semanticDegradedMessage = health.semantic_message || "Semantic search degraded: run 'ollama pull all-minilm:l6'";
      renderDegradedBanner();
    } else {
      semanticDegradedMessage = null;
      $("#semantic-degraded-banner").remove();
    }
  } catch {
    /* ignore network issues on public browse */
  }
}
function renderDegradedBanner(): void {
  if (!semanticDegradedMessage) return;
  if ($("#semantic-degraded-banner").length === 0) {
    const banner = $(`<div id="semantic-degraded-banner" style="background:#dc2626;color:#fff;padding:8px 16px;font-size:12px;font-weight:600;display:flex;justify-content:space-between;align-items:center;z-index:9999;position:sticky;top:0"><span>⚠️ ${e(semanticDegradedMessage)}</span><button style="background:transparent;border:none;color:#fff;cursor:pointer;font-weight:700" onclick="$('#semantic-degraded-banner').remove()">${icon("x")}</button></div>`);
    $("body").prepend(banner);
    createIcons({ icons });
  }
}

window.addEventListener("hashchange", () => void navigate());
async function start(): Promise<void> {
  void checkSystemHealth();
  if (localStorage.getItem("sm-session") === "active") {
    try {
      user = await refreshSession();
      await loadPreferences();
      startNotifications();
    } catch {
      localStorage.removeItem("sm-session");
    }
  }
  await navigate();
}
workspace.init({
  shell,
  heading,
  jobCard,
  toast,
  user: () => user,
  navigate,
  finish,
});
applyTheme();
void start();
