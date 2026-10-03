"""Exercise migration preservation against real pre-upgrade SQLite rows."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def test_populated_upgrade_and_empty_downgrade(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    path = tmp_path / "upgrade.db"
    env = {**os.environ, "DATABASE_URL": "sqlite:///" + path.as_posix()}

    def migrate(*args):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args], cwd=backend, env=env, capture_output=True, text=True
        )
        assert result.returncode == 0, result.stderr

    migrate("upgrade", "ea131b083c8f")
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO users (id,email,name,password_hash,role,active,token_version,created_at) VALUES (1,'catalog@skillmatch.example','Catalog','disabled','recruiter',0,0,CURRENT_TIMESTAMP)"
        )
        db.execute(
            "INSERT INTO users (id,email,name,password_hash,role,active,token_version,created_at) VALUES (2,'candidate@example.com','Candidate','disabled','candidate',1,0,CURRENT_TIMESTAMP)"
        )
        db.execute(
            "INSERT INTO jobs (id,recruiter_id,title,company,location,employment_type,description,salary_min,salary_max,active,created_at) VALUES (1,1,'Engineer','Acme','Remote','Full-time','Python',100,200,1,CURRENT_TIMESTAMP)"
        )
        db.execute("INSERT INTO skills (id,name,category) VALUES (1,'Python','Technology')")
        db.execute("INSERT INTO job_skills VALUES (1,1)")
        db.execute(
            "INSERT INTO resumes (id,user_id,filename,text,created_at) VALUES (1,2,'resume.docx','Python',CURRENT_TIMESTAMP)"
        )
        db.execute("INSERT INTO resume_skills VALUES (1,1)")
        db.execute(
            "INSERT INTO applications (id,user_id,job_id,resume_id,status,created_at) VALUES (1,2,1,1,'Applied',CURRENT_TIMESTAMP)"
        )
        db.execute(
            "INSERT INTO match_results (id,resume_id,job_id,score,semantic_score,keyword_score,matched,missing,method,created_at) VALUES (1,1,1,100,0,100,'[\"Python\"]','[]','keyword',CURRENT_TIMESTAMP)"
        )
    migrate("upgrade", "head")
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        for table in ["job_skills", "resume_skills", "applications", "match_results"]:
            assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 1
        assert db.execute("SELECT is_demo,source FROM jobs").fetchone() == (1, "demo")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("UPDATE applications SET status='Offer'")
        db.commit()
        db.execute("DELETE FROM resumes")
        assert db.execute("SELECT resume_id FROM applications").fetchone()[0] is None
    empty = tmp_path / "empty.db"
    env["DATABASE_URL"] = "sqlite:///" + empty.as_posix()
    migrate("upgrade", "head")
    migrate("downgrade", "ea131b083c8f")
    migrate("upgrade", "head")
