import logging
from sqlalchemy import select
from app.db import SessionLocal
from app.models import Application, ApplicationEvent, Job, MatchResult, Resume, Skill, User
from app.security import password_hash
from app.services.matching import save_match
from app.services.taxonomy import ensure_taxonomy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_candidates")

DUMMY_CANDIDATES = [
    {
        "name": "Priya Sharma",
        "email": "priya.sharma@example.com",
        "roles": ["Senior Full-Stack Engineer", "Frontend Tech Lead"],
        "experience": 4.5,
        "filename": "Priya_Sharma_FullStack.pdf",
        "skills": ["Python", "TypeScript", "React", "PostgreSQL", "Docker", "Next.js", "FastAPI", "Node.js"],
        "text": """# Priya Sharma - Senior Full-Stack Engineer
Email: priya.sharma@example.com | Bengaluru, India / Remote | LinkedIn & GitHub

SUMMARY:
Senior Full-Stack Engineer with 4.5+ years of experience building performant, modern web applications. 
Specialized in React, TypeScript, Next.js, and high-performance Python FastAPI / Node.js backends. 
Passionate about scalable architecture, elegant UI/UX, and cloud containerization.

EXPERIENCE:
Senior Software Engineer - TechVanguard Solutions (2022 - Present)
- Architected and delivered a multi-tenant enterprise analytics dashboard in React, TypeScript, and FastAPI, serving 120k daily active users.
- Redesigned backend query pipelines in PostgreSQL and Redis, cutting p95 response latency from 450ms to 65ms.
- Containerized development and staging pipelines using Docker and Kubernetes, streamlining onboarding and CI/CD releases.

Full-Stack Developer - CloudScale Labs (2020 - 2022)
- Built interactive frontend components and design systems using Next.js and Tailwind CSS.
- Developed RESTful microservices in Python and Node.js with automated test coverage exceeding 90%.

EDUCATION:
B.Tech in Computer Science & Engineering - National Institute of Technology (NIT)

SKILLS:
React, TypeScript, JavaScript, Python, FastAPI, Node.js, Next.js, PostgreSQL, Docker, Git, CI/CD, REST APIs
"""
    },
    {
        "name": "Aarav Patel",
        "email": "aarav.devops@example.com",
        "roles": ["Cloud & DevOps Architect", "Site Reliability Engineer"],
        "experience": 6.0,
        "filename": "Aarav_Patel_DevOps_Architect.pdf",
        "skills": ["Kubernetes", "Docker", "AWS", "Terraform", "CI/CD", "Linux", "Python", "Prometheus"],
        "text": """# Aarav Patel - Cloud & DevOps Architect
Email: aarav.devops@example.com | Pune, India / Remote

SUMMARY:
Senior DevOps and Cloud Infrastructure Architect with 6 years of experience designing, deploying, 
and automating resilient multi-cloud environments on AWS and GCP. Extensive production experience 
orchestrating Kubernetes clusters, writing Terraform IaC modules, and instituting automated CI/CD pipelines.

EXPERIENCE:
Lead Cloud Infrastructure Engineer - NexaCloud Systems (2021 - Present)
- Designed and scaled zero-downtime Kubernetes infrastructure supporting 40M+ monthly transactions across multi-region AWS deployments.
- Standardized infrastructure-as-code using Terraform, cutting cloud deployment times by 65% and reducing infrastructure drift.
- Set up automated telemetry, alerting, and observability stacks utilizing Prometheus, Grafana, and OpenTelemetry.

DevOps Engineer - Apex Global (2018 - 2021)
- Spearheaded company-wide migration from monolithic VM hosting to containerized Docker workloads on AWS EKS.
- Built automated GitHub Actions and GitLab CI/CD pipelines for 30+ microservice repositories.

SKILLS:
Kubernetes, Docker, AWS, Terraform, CI/CD, Linux, Python, Prometheus, Grafana, Microservices, Git
"""
    },
    {
        "name": "Ananya Iyer",
        "email": "ananya.ds@example.com",
        "roles": ["Machine Learning Engineer", "NLP Specialist"],
        "experience": 3.5,
        "filename": "Ananya_Iyer_ML_Engineer.pdf",
        "skills": ["Python", "PyTorch", "Machine Learning", "NLP", "Pandas", "SQL", "Scikit-Learn", "FastAPI"],
        "text": """# Ananya Iyer - Machine Learning & NLP Specialist
Email: ananya.ds@example.com | Hyderabad, India / Remote

SUMMARY:
Machine Learning Engineer with 3.5 years of experience researching and deploying production NLP, 
embeddings, and retrieval-augmented generation (RAG) models. Proficient in PyTorch, transformers, 
semantic vector search, and data engineering pipelines.

EXPERIENCE:
Machine Learning Engineer - Cognition AI Labs (2022 - Present)
- Developed transformer-based text extraction and semantic matching pipelines delivering 94% relevance precision.
- Engineered vector search indexing using pgvector and PyTorch embeddings for semantic document retrieval.
- Deployed low-latency inference APIs with FastAPI and ONNX runtime under 50ms latency.

Data Scientist - QuantEdge Analytics (2021 - 2022)
- Implemented predictive clustering and classification pipelines with Scikit-Learn, Pandas, and SQL.
- Designed automated feature stores and validation scripts to monitor data drift.

SKILLS:
Python, PyTorch, Machine Learning, NLP, Pandas, SQL, Scikit-Learn, FastAPI, Git, Statistics
"""
    },
    {
        "name": "Rohan Verma",
        "email": "rohan.backend@example.com",
        "roles": ["Senior Backend Engineer", "Distributed Systems Engineer"],
        "experience": 5.0,
        "filename": "Rohan_Verma_Backend_Systems.pdf",
        "skills": ["Python", "Go", "PostgreSQL", "Redis", "Kafka", "System Design", "Microservices", "SQL"],
        "text": """# Rohan Verma - Senior Backend Systems Engineer
Email: rohan.backend@example.com | Mumbai, India / Remote

SUMMARY:
Backend Engineer with 5 years specializing in distributed systems, event-driven architectures, 
and high-throughput data processing. Strong expertise in Python, Go, Kafka, PostgreSQL, and Redis.

EXPERIENCE:
Senior Backend Engineer - Streamline FinTech (2021 - Present)
- Architected distributed ledger service in Go and Python processing 15,000 requests/second with 99.99% uptime.
- Built asynchronous event-driven pipelines utilizing Apache Kafka and Redis caching layers.
- Optimized complex PostgreSQL indexes and query plans, eliminating bottlenecks on high-write payment tables.

Software Engineer - DataMatrix (2019 - 2021)
- Developed secure REST and gRPC microservices in Python with SQLAlchemy and Docker.
- Maintained background worker queues and scheduled cron jobs.

SKILLS:
Python, Go, PostgreSQL, Redis, Kafka, System Design, Microservices, SQL, Docker, Linux, REST APIs
"""
    }
]

def seed():
    with SessionLocal() as db:
        all_skills = {s.name.casefold(): s for s in ensure_taxonomy(db)}
        active_jobs = list(db.scalars(select(Job).where(Job.active.is_(True))).all())
        logger.info("Found %d active jobs in database for matching.", len(active_jobs))

        # Prioritize recruiter jobs, then top recent jobs
        recruiter_jobs = [j for j in active_jobs if j.recruiter_id is not None]
        other_jobs = [j for j in active_jobs if j.recruiter_id is None][:15]
        target_jobs = recruiter_jobs + other_jobs
        logger.info("Scoring against %d target jobs per candidate.", len(target_jobs))

        for item in DUMMY_CANDIDATES:
            user = db.scalar(select(User).where(User.email == item["email"]))
            if not user:
                user = User(
                    name=item["name"],
                    email=item["email"],
                    password_hash=password_hash.hash("CandidatePass123!"),
                    role="candidate",
                    preferences={"preferred_roles": item["roles"]},
                    email_verified=True,
                )
                db.add(user)
                db.flush()
                logger.info("Created candidate user: %s (%s)", user.name, user.email)
            else:
                user.preferences = {"preferred_roles": item["roles"]}
                db.flush()

            # Ensure resume exists
            resume = db.scalar(select(Resume).where(Resume.user_id == user.id))
            matched_skills = []
            for s_name in item["skills"]:
                s_obj = all_skills.get(s_name.casefold())
                if not s_obj:
                    s_obj = db.scalar(select(Skill).where(Skill.name.ilike(s_name)))
                if not s_obj:
                    s_obj = Skill(name=s_name, category="Technology")
                    db.add(s_obj)
                    db.flush()
                    all_skills[s_name.casefold()] = s_obj
                matched_skills.append(s_obj)

            if not resume:
                resume = Resume(
                    user_id=user.id,
                    filename=item["filename"],
                    text=item["text"],
                    experience_years=item["experience"],
                    skills=matched_skills,
                    is_primary=True,
                )
                db.add(resume)
                db.flush()
                logger.info("Created resume for %s with %d skills", user.name, len(matched_skills))
            else:
                resume.skills = matched_skills
                resume.experience_years = item["experience"]
                db.flush()

            # Score against target jobs
            for job in target_jobs:
                save_match(db, resume, job)
            db.commit()
            logger.info("Committed candidate %s and matches.", user.name)

        # Make sure demo_candidate has a resume too if missing
        demo_candidate = db.scalar(select(User).where(User.email == "demo_candidate@gmail.com"))
        if demo_candidate:
            cand_res = db.scalar(select(Resume).where(Resume.user_id == demo_candidate.id))
            if not cand_res:
                cand_skills = [all_skills[k] for k in ["python", "react", "sql"] if k in all_skills]
                cand_res = Resume(
                    user_id=demo_candidate.id,
                    filename="Demo_Candidate_Resume.pdf",
                    text="# Demo Candidate\nExperienced Frontend & Python Developer with strong UI skills.",
                    experience_years=3.0,
                    skills=cand_skills,
                    is_primary=True
                )
                db.add(cand_res)
                db.flush()
                for job in target_jobs:
                    save_match(db, cand_res, job)
            db.commit()

        # Let's also create 1-2 realistic applications for recruiter jobs if recruiter has any jobs
        recruiter = db.scalar(select(User).where(User.role == "recruiter"))
        if recruiter:
            recruiter_jobs = list(db.scalars(select(Job).where(Job.recruiter_id == recruiter.id)).all())
            if recruiter_jobs:
                target_job = recruiter_jobs[0]
                candidates = list(db.scalars(select(User).where(User.role == "candidate")).all())
                statuses = ["Applied", "Interview", "Reviewing"]
                for i, cand in enumerate(candidates[:3]):
                    existing_app = db.scalar(
                        select(Application).where(Application.user_id == cand.id, Application.job_id == target_job.id)
                    )
                    cand_res = db.scalar(select(Resume).where(Resume.user_id == cand.id))
                    if not existing_app and cand_res:
                        app = Application(
                            user_id=cand.id,
                            job_id=target_job.id,
                            resume_id=cand_res.id,
                            status=statuses[i % len(statuses)]
                        )
                        db.add(app)
                        db.flush()
                        db.add(ApplicationEvent(application_id=app.id, actor_id=cand.id, status=app.status, note="Initial review"))

        db.commit()
        logger.info("Successfully seeded dummy candidates and scored against active jobs!")

if __name__ == "__main__":
    seed()
