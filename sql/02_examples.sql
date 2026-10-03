-- Run after migrations and `python -m app.seed`.
-- Teaching examples use synthetic catalog data, with no shared login credentials.
BEGIN;
INSERT INTO skills (name, category) VALUES ('OpenTelemetry', 'Cloud & DevOps')
ON CONFLICT (name) DO NOTHING;

-- Filter and order jobs, with pagination.
SELECT id, title, company, location, salary_min, salary_max
FROM jobs
WHERE active = true AND location = 'Remote' AND salary_min >= 120000
ORDER BY salary_max DESC, id
LIMIT 10 OFFSET 0;

-- Most frequently requested skills.
SELECT s.name, COUNT(js.job_id) AS job_count
FROM skills s
JOIN job_skills js ON js.skill_id = s.id
JOIN jobs j ON j.id = js.job_id
WHERE j.active = true
GROUP BY s.id, s.name
ORDER BY job_count DESC, s.name
LIMIT 10;

-- Match results with candidate names. In the application this query is owner-scoped.
SELECT j.title, u.name, mr.score, mr.keyword_score, mr.semantic_score, mr.method
FROM match_results mr
JOIN jobs j ON j.id = mr.job_id
JOIN resumes r ON r.id = mr.resume_id
JOIN users u ON u.id = r.user_id
ORDER BY mr.score DESC;

-- Applications by calendar date.
SELECT CAST(created_at AS DATE) AS applied_on, COUNT(*) AS applications
FROM applications
GROUP BY CAST(created_at AS DATE)
ORDER BY applied_on;

-- Average advertised salary by employment type.
SELECT employment_type, COUNT(*) AS openings,
       ROUND(AVG((salary_min + salary_max) / 2.0), 2) AS average_midpoint
FROM jobs WHERE active = true
GROUP BY employment_type;

-- Demonstrate update and delete without modifying the persisted catalog.
UPDATE skills SET category = 'Observability' WHERE name = 'OpenTelemetry';
DELETE FROM skills WHERE name = 'OpenTelemetry';
ROLLBACK;
