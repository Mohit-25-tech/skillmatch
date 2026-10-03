export interface Preferences {
  theme: "dark" | "light" | "system";
  preferred_roles: string[];
  locations: string[];
  remote_preference: "any" | "remote" | "onsite";
  salary_expectation: number | null;
  salary_currency: string | null;
  salary_interval: "hour" | "month" | "year";
  job_alerts: boolean;
  email_digest: boolean;
  discoverable: boolean;
}
export interface Profile {
  name: string;
  preferences: Preferences;
}
export interface Tracker {
  id: number;
  job: import("./types").Job;
  status: string;
  notes: string;
  custom_company?: string | null;
  custom_title?: string | null;
  custom_url?: string | null;
  follow_up_at?: string | null;
  created_at: string;
  updated_at: string;
  timeline: { id: number; status: string; note: string; created_at: string }[];
}
export interface Notice {
  id: number;
  title: string;
  job_id: number;
  read: boolean;
  created_at: string;
}
export interface Notices {
  items: Notice[];
  unread: number;
  next_cursor: number;
}
export interface Learning {
  skill: string;
  related_jobs: number;
  message?: string;
  resources: { title: string; url: string; provider: string }[];
}
export interface ATS {
  score: number;
  sections: Record<string, boolean>;
  checks: Record<string, boolean>;
  word_count: number;
  keyword_coverage: number | null;
  missing_keywords: string[];
  method: string;
}
export interface SavedSearch {
  id: number;
  name: string;
  filters: {
    keywords: string;
    location: string;
    kind: string;
    min_match: number;
  };
  alerts: boolean;
}
export interface Market {
  active_jobs: number;
  skills: Record<string, number>;
  companies: Record<string, number>;
  locations: Record<string, number>;
  types: Record<string, number>;
  salaries: {
    role: string;
    location: string;
    currency: string;
    interval: string;
    count: number;
    average: number;
    min: number;
    max: number;
    values: number[];
  }[];
  history: {
    day: string;
    skills: Record<string, number>;
    active_jobs: number;
  }[];
  generated_at: string;
}
export interface Source {
  id: number;
  key: string;
  kind: string;
  config: Record<string, string | number>;
  enabled: boolean;
  interval_minutes: number;
  status: string;
  stats: Record<string, number | boolean>;
  last_run_at: string | null;
  last_error: string | null;
}
