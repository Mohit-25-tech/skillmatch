-- Generated from the versioned Alembic migration. PostgreSQL dialect.
BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> ea131b083c8f

CREATE TABLE skills (
    id SERIAL NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    category VARCHAR(60) NOT NULL, 
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_skills_name ON skills (name);

CREATE TABLE users (
    id SERIAL NOT NULL, 
    email VARCHAR(254) NOT NULL, 
    name VARCHAR(100) NOT NULL, 
    password_hash VARCHAR(255) NOT NULL, 
    role VARCHAR(20) NOT NULL, 
    active BOOLEAN NOT NULL, 
    token_version INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (role IN ('candidate','recruiter','admin'))
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE TABLE jobs (
    id SERIAL NOT NULL, 
    recruiter_id INTEGER NOT NULL, 
    title VARCHAR(150) NOT NULL, 
    company VARCHAR(100) NOT NULL, 
    location VARCHAR(100) NOT NULL, 
    employment_type VARCHAR(30) NOT NULL, 
    description TEXT NOT NULL, 
    salary_min INTEGER NOT NULL, 
    salary_max INTEGER NOT NULL, 
    active BOOLEAN NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (salary_min >= 0 AND salary_max >= salary_min), 
    FOREIGN KEY(recruiter_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_jobs_active ON jobs (active);

CREATE INDEX ix_jobs_location_type ON jobs (location, employment_type);

CREATE INDEX ix_jobs_recruiter_id ON jobs (recruiter_id);

CREATE INDEX ix_jobs_title ON jobs (title);

CREATE TABLE refresh_sessions (
    id VARCHAR(64) NOT NULL, 
    user_id INTEGER NOT NULL, 
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_refresh_sessions_user_id ON refresh_sessions (user_id);

CREATE TABLE resumes (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    filename VARCHAR(255) NOT NULL, 
    text TEXT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_resumes_user_id ON resumes (user_id);

CREATE TABLE applications (
    id SERIAL NOT NULL, 
    user_id INTEGER NOT NULL, 
    job_id INTEGER NOT NULL, 
    resume_id INTEGER NOT NULL, 
    status VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (status IN ('Applied','Reviewing','Interview','Rejected','Hired')), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE CASCADE, 
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
    CONSTRAINT uq_application_user_job UNIQUE (user_id, job_id)
);

CREATE INDEX ix_applications_job_id ON applications (job_id);

CREATE INDEX ix_applications_user_id ON applications (user_id);

CREATE TABLE job_skills (
    job_id INTEGER NOT NULL, 
    skill_id INTEGER NOT NULL, 
    PRIMARY KEY (job_id, skill_id), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

CREATE TABLE match_results (
    id SERIAL NOT NULL, 
    resume_id INTEGER NOT NULL, 
    job_id INTEGER NOT NULL, 
    score FLOAT NOT NULL, 
    semantic_score FLOAT NOT NULL, 
    keyword_score FLOAT NOT NULL, 
    matched JSON NOT NULL, 
    missing JSON NOT NULL, 
    method VARCHAR(30) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CHECK (score >= 0 AND score <= 100), 
    FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE CASCADE, 
    FOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE CASCADE, 
    CONSTRAINT uq_match_resume_job UNIQUE (resume_id, job_id)
);

CREATE INDEX ix_match_results_job_id ON match_results (job_id);

CREATE INDEX ix_match_results_resume_id ON match_results (resume_id);

CREATE TABLE resume_skills (
    resume_id INTEGER NOT NULL, 
    skill_id INTEGER NOT NULL, 
    PRIMARY KEY (resume_id, skill_id), 
    FOREIGN KEY(resume_id) REFERENCES resumes (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('ea131b083c8f') RETURNING alembic_version.version_num;

COMMIT;

