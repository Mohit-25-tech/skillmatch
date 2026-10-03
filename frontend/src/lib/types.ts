export interface User {
  id: number;
  name: string;
  email: string;
  role: "candidate" | "recruiter" | "admin";
  active: boolean;
}
export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  employment_type: string;
  description: string;
  salary_min: number | null;
  salary_max: number | null;
  skills: string[];
  created_at: string;
  score?: number | null;
  source?: string;
  saved?: boolean;
  is_demo?: boolean;
  remote?: boolean;
  program_badge?: string | null;
  confidence?: "high" | "low";
  confidence_label?: string;
  posted_at?: string | null;
  last_seen_at?: string | null;
  apply_url?: string | null;
  salary_currency?: string | null;
  salary_interval?: string | null;
  sources?: { name: string; url: string; apply_url: string }[];
  match?: Match | null;
  active?: boolean;
  experience_level?: string | null;
  country?: string | null;
}
export interface Resume {
  id: number;
  filename: string;
  skills: string[];
  created_at: string;
  is_primary?: boolean;
  parse_warnings?: string[];
  experience_years?: number | null;
}
export interface Match {
  id: number;
  job_id: number;
  resume_id: number;
  score: number;
  semantic_score: number;
  keyword_score: number;
  matched: string[];
  missing: string[];
  method: string;
  confidence?: "high" | "low";
  confidence_label?: string;
  job: Job;
  components?: Record<string, { score: number | null; weight: number }>;
  reasons?: string[];
  improvements?: string[];
  suggestions: { skill: string; title: string; url: string }[];
}
export interface Application {
  id: number;
  job: Job;
  candidate: string;
  status: string;
  score: number | null;
  created_at: string;
}
export interface Analytics {
  matches: number;
  average_score: number;
  applications: number;
  interviews: number;
  skill_gaps: Record<string, number>;
  score_distribution: number[];
  in_demand: Record<string, number>;
  applications_over_time: Record<string, number>;
  candidate_pool?: number;
  my_jobs_count?: number;
}
export interface CandidateProfile {
  id: number;
  name: string;
  email: string;
  headline: string;
  experience_years: number;
  skills: string[];
  resume_id: number;
  resume_filename: string;
  resume_text: string;
  snippet: string;
  match_score: number | null;
  matched_job_title?: string | null;
  applications: {
    application_id: number;
    job_id: number;
    job_title: string;
    status: string;
    applied_at: string;
  }[];
  created_at: string;
}

