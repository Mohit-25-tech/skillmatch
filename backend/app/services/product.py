"""Database-backed product services shared by API and worker."""

import re
import smtplib
from collections import Counter, defaultdict
from datetime import timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    InsightCache,
    InsightSnapshot,
    Job,
    LearningResource,
    MatchResult,
    Notification,
    Resume,
    SavedSearch,
    Skill,
    User,
    utcnow,
)


def latest_resume(db: Session, user_id: int):
    return db.scalar(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.is_primary.desc(), Resume.id.desc())
        .limit(1)
    )


def visible_jobs():
    return select(Job).where(Job.active.is_(True), Job.is_demo.is_(False))


def create_alerts(db: Session, resume: Resume) -> None:
    user = db.get(User, resume.user_id)
    if not user or not user.preferences.get("job_alerts", True):
        return
    for search in db.scalars(
        select(SavedSearch).where(SavedSearch.user_id == user.id, SavedSearch.alerts.is_(True))
    ).all():
        filters = search.filters
        rows = db.execute(
            select(Job, MatchResult)
            .join(MatchResult, MatchResult.job_id == Job.id)
            .where(
                MatchResult.resume_id == resume.id,
                MatchResult.score >= filters.get("min_match", 0),
                Job.active.is_(True),
                Job.is_demo.is_(False),
                Job.created_at >= search.created_at,
            )
        ).all()
        for job, match in rows:
            if (
                filters.get("keywords", "").casefold()
                not in (job.title + " " + job.company + " " + job.description).casefold()
            ):
                continue
            if filters.get("location", "").casefold() not in job.location.casefold():
                continue
            if filters.get("kind") and filters["kind"] != job.employment_type:
                continue
            if db.scalar(
                select(Notification.id).where(
                    Notification.user_id == user.id,
                    Notification.search_id == search.id,
                    Notification.job_id == job.id,
                )
            ):
                continue
            db.add(
                Notification(
                    user_id=user.id,
                    search_id=search.id,
                    job_id=job.id,
                    title=f"{job.title} at {job.company}"[:250],
                )
            )
    db.flush()


def send_digests(db: Session) -> int:
    settings = get_settings()
    if not settings.smtp_host:
        return 0
    count = 0
    for user in db.scalars(select(User).where(User.active.is_(True))).all():
        if not user.preferences.get("email_digest") or not user.preferences.get("job_alerts", True):
            continue
        rows = db.scalars(
            select(Notification)
            .join(SavedSearch)
            .where(
                Notification.user_id == user.id,
                Notification.emailed_at.is_(None),
                SavedSearch.alerts.is_(True),
            )
            .order_by(Notification.id)
            .limit(100)
        ).all()
        if not rows:
            continue
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = (
            settings.smtp_from,
            user.email,
            "Your SkillMatch job alerts",
        )
        from app.repositories.catalog import job_public

        lines = []
        for item in rows:
            job = db.get(Job, item.job_id)
            if job and job.active:
                public = job_public(job)
                attribution = "\n".join(
                    f"Source: {source['name']} - {source['url']}" for source in public["sources"]
                )
                lines.append(
                    f"{item.title}\n{public['apply_url'] or 'Open your SkillMatch workspace to view this native job.'}\n{attribution}".strip()
                )
        if lines:
            lines.append(
                f"\n---\nTo update your alert preferences or unsubscribe, visit: {settings.frontend_url}/#settings or {settings.frontend_url}/api/v1/auth/unsubscribe?email={user.email}"
            )
            message.set_content("\n\n".join(lines))
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
        for item in rows:
            item.emailed_at = utcnow()
        db.commit()
        count += len(rows)
    return count


def ats_report(resume: Resume, job: Job | None = None) -> dict:
    text = resume.text
    words = len(text.split())
    sections = {
        name: bool(re.search(pattern, text, re.I | re.M))
        for name, pattern in {
            "experience": r"\b(experience|employment|work history|projects|internships|academic projects)\b",
            "education": r"\b(education|degree|university)\b",
            "skills": r"\b(skills|technologies|competencies)\b",
            "contact": r"[\w.+-]+@[\w.-]+\.[a-z]{2,}",
        }.items()
    }
    checks = {
        "readable_length": 250 <= words <= 1500,
        "achievement_bullets": bool(re.search(r"^\s*[-•*]\s+", text, re.M)),
        "no_replacement_characters": "\ufffd" not in text,
    }
    have = {s.name for s in resume.skills}
    required = {s.name for s in job.skills} if job else set()
    coverage = round(100 * len(have & required) / len(required), 1) if required else None
    measured = [100 * sum(sections.values()) / 4, 100 * sum(checks.values()) / 3]
    if coverage is not None:
        measured.append(coverage)
    return {
        "score": round(sum(measured) / len(measured), 1),
        "sections": sections,
        "checks": checks,
        "word_count": words,
        "keyword_coverage": coverage,
        "missing_keywords": sorted(required - have),
        "method": "Text-based heuristic; not a prediction of any employer ATS. Original visual layout is not scored.",
    }


def candidate_matches_summary(db: Session, user_id: int) -> dict:
    resume = latest_resume(db, user_id)
    active_total = db.scalar(select(func.count()).select_from(visible_jobs().subquery())) or 0
    if not resume:
        return {
            "resume_id": None,
            "total_matches": 0,
            "average_score": 0.0,
            "active_jobs": active_total,
            "scored_jobs": 0,
            "pending_jobs": 0,
            "requires_resume": True,
        }
    scores = db.scalars(
        select(MatchResult.score)
        .join(Job)
        .where(
            MatchResult.resume_id == resume.id,
            Job.active.is_(True),
            Job.is_demo.is_(False),
        )
        .order_by(MatchResult.score.desc(), Job.id.desc())
    ).all()
    count = len(scores)
    avg = round(sum(scores) / count, 1) if count else 0.0
    return {
        "resume_id": resume.id,
        "total_matches": count,
        "average_score": avg,
        "active_jobs": active_total,
        "scored_jobs": count,
        "pending_jobs": max(0, active_total - count),
        "requires_resume": False,
    }


GENERIC_OR_SOFT_SKILLS = {
    "communication",
    "collaboration",
    "computer science",
    "problem solving",
    "teamwork",
    "leadership",
    "critical thinking",
    "adaptability",
    "time management",
    "analytical skills",
    "presentation",
    "research",
    "mentoring",
    "creativity",
    "work ethic",
    "attention to detail",
    "interpersonal skills",
}


def learning_path(db: Session, resume: Resume | None) -> list:
    if not resume:
        return []
    results = db.scalars(
        select(MatchResult)
        .join(Job)
        .where(MatchResult.resume_id == resume.id, Job.active.is_(True), Job.is_demo.is_(False))
    ).all()

    unlocks_counter: Counter[str] = Counter()
    total_missing_counter: Counter[str] = Counter()

    for result in results:
        missing_tech = [
            s for s in (result.missing or [])
            if s.casefold() not in GENERIC_OR_SOFT_SKILLS
        ]
        for s in missing_tech:
            total_missing_counter[s] += 1
            # A skill unlocks a role if the candidate is only 1 or 2 skills away from full qualification
            if 1 <= len(missing_tech) <= 2:
                unlocks_counter[s] += 1

    ranking_counter = unlocks_counter if unlocks_counter else total_missing_counter

    resources = defaultdict(list)
    for resource, name in db.execute(select(LearningResource, Skill.name).join(Skill)).all():
        resources[name].append({"title": resource.title, "url": resource.url, "provider": resource.provider})

    path_items = []
    ranked_skills = sorted(
        ranking_counter.keys(),
        key=lambda s: (unlocks_counter.get(s, 0), total_missing_counter.get(s, 0)),
        reverse=True,
    )

    for name in ranked_skills:
        unlock_n = unlocks_counter.get(name, 0)
        tot_n = total_missing_counter.get(name, 0)
        target_count = unlock_n if unlock_n > 0 else tot_n
        msg = f"Learning {name} unlocks {target_count} more job{'s' if target_count != 1 else ''}"
        path_items.append({
            "skill": name,
            "related_jobs": target_count,
            "unlocks_count": unlock_n,
            "message": msg,
            "resources": resources.get(name, []),
        })
    return path_items


def seed_resources(db: Session) -> None:
    catalog = [
        ("Python", "Python 3 Official Tutorial", "https://docs.python.org/3/tutorial/", "Python.org"),
        ("JavaScript", "JavaScript Guide & Reference", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "MDN"),
        ("TypeScript", "TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html", "TypeScript"),
        ("React", "React Documentation & Tutorials", "https://react.dev/learn", "React"),
        ("Next.js", "Learn Next.js App Router", "https://nextjs.org/learn", "Next.js"),
        ("Node.js", "Node.js Getting Started Guide", "https://nodejs.org/en/learn/getting-started/introduction-to-nodejs", "Node.js"),
        ("HTML", "HTML: Structuring the Web", "https://developer.mozilla.org/en-US/docs/Learn/HTML", "MDN"),
        ("CSS", "Learn CSS & Responsive Design", "https://developer.mozilla.org/en-US/docs/Learn/CSS", "MDN"),
        ("SQL", "Relational Database & SQL Tutorial", "https://www.freecodecamp.org/news/sql-and-databases-full-course/", "freeCodeCamp"),
        ("PostgreSQL", "PostgreSQL Official Tutorial", "https://www.postgresql.org/docs/current/tutorial.html", "PostgreSQL.org"),
        ("Docker", "Docker Official Getting Started Guide", "https://docs.docker.com/get-started/", "Docker"),
        ("Kubernetes", "Kubernetes Basics & Tutorials", "https://kubernetes.io/docs/tutorials/kubernetes-basics/", "Kubernetes.io"),
        ("Git", "Pro Git Book (Free Online)", "https://git-scm.com/book/en/v2", "Git-SCM"),
        ("Go", "A Tour of Go", "https://go.dev/tour/", "Go.dev"),
        ("Rust", "The Rust Programming Language Book", "https://doc.rust-lang.org/book/", "Rust-Lang.org"),
        ("Java", "Java Tutorials & Language Basics", "https://dev.java/learn/", "dev.java"),
        ("C++", "C++ Tutorial and Core Concepts", "https://www.learncpp.com/", "LearnCpp"),
        ("C", "CS50 Introduction to Computer Science", "https://cs50.harvard.edu/x/", "CS50"),
        ("Linux", "Linux Journey - Command Line & Systems", "https://linuxjourney.com/", "Linux Journey"),
        ("AWS", "AWS Cloud Practitioner Essentials", "https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/", "AWS"),
        ("Google Cloud", "Google Cloud Architecture & Fundamentals", "https://cloud.google.com/learn", "Google Cloud"),
        ("Azure", "Microsoft Azure Fundamentals Path", "https://learn.microsoft.com/en-us/training/paths/microsoft-azure-fundamentals-describe-cloud-concepts/", "Microsoft Learn"),
        ("FastAPI", "FastAPI Step-by-Step Tutorial", "https://fastapi.tiangolo.com/tutorial/", "FastAPI"),
        ("Django", "Django Official Getting Started", "https://docs.djangoproject.com/en/stable/intro/tutorial01/", "Django"),
        ("Flask", "Flask Official Quickstart", "https://flask.palletsprojects.com/en/latest/quickstart/", "Pallets"),
        ("PyTorch", "PyTorch Tutorials & Deep Learning Recipes", "https://pytorch.org/tutorials/", "PyTorch.org"),
        ("TensorFlow", "TensorFlow Core Tutorials", "https://www.tensorflow.org/tutorials", "TensorFlow.org"),
        ("Scikit-learn", "Scikit-Learn Machine Learning Guide", "https://scikit-learn.org/stable/user_guide.html", "Scikit-learn"),
        ("Pandas", "Pandas Getting Started & User Guide", "https://pandas.pydata.org/docs/getting_started/index.html", "Pandas"),
        ("NumPy", "NumPy the Absolute Basics", "https://numpy.org/doc/stable/user/absolute_beginners.html", "NumPy"),
        ("Large Language Models", "Hugging Face Open LLM Course", "https://huggingface.co/learn/llm-course/chapter1/1", "Hugging Face"),
        ("NLP", "Hugging Face Natural Language Processing Course", "https://huggingface.co/learn/nlp-course/", "Hugging Face"),
        ("Computer Vision", "PyTorch Computer Vision Recipes", "https://pytorch.org/tutorials/intermediate/torchvision_tutorial.html", "PyTorch"),
        ("MLOps", "MLOps Roadmap & Best Practices", "https://roadmap.sh/mlops", "roadmap.sh"),
        ("GraphQL", "Introduction to GraphQL", "https://graphql.org/learn/", "GraphQL.org"),
        ("Redis", "Redis University & Quick Start", "https://redis.io/learn/howtos/quick-start", "Redis"),
        ("MongoDB", "MongoDB Free Developer Courses", "https://learn.mongodb.com/", "MongoDB University"),
        ("Kafka", "Apache Kafka Quickstart", "https://kafka.apache.org/quickstart", "Apache Kafka"),
        ("Elasticsearch", "Elasticsearch Getting Started", "https://www.elastic.co/guide/en/elasticsearch/reference/current/getting-started.html", "Elastic"),
        ("CI/CD", "GitHub Actions Complete Guide", "https://docs.github.com/en/actions/learn-github-actions", "GitHub Docs"),
        ("Terraform", "HashiCorp Terraform Tutorials", "https://developer.hashicorp.com/terraform/tutorials", "HashiCorp"),
        ("Ansible", "Ansible Community Getting Started", "https://docs.ansible.com/ansible/latest/getting_started/index.html", "Ansible"),
        ("SRE", "Google Site Reliability Engineering Book", "https://sre.google/sre-book/table-of-contents/", "Google SRE"),
        ("DevOps", "DevOps Engineer Roadmap", "https://roadmap.sh/devops", "roadmap.sh"),
        ("Web Development", "Frontend Developer Roadmap", "https://roadmap.sh/frontend", "roadmap.sh"),
        ("Backend", "Backend Developer Roadmap", "https://roadmap.sh/backend", "roadmap.sh"),
        ("Microservices", "Microservices Guide by Martin Fowler", "https://martinfowler.com/microservices/", "MartinFowler"),
        ("System Design", "System Design Primer", "https://github.com/donnemartin/system-design-primer", "System Design Primer"),
        ("Data Structures", "CS50 Data Structures & Algorithms", "https://cs50.harvard.edu/x/2024/weeks/5/", "CS50"),
        ("Algorithms", "freeCodeCamp Algorithms & Problem Solving", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/", "freeCodeCamp"),
        ("Data Engineering", "Data Engineering Zoomcamp (Free)", "https://github.com/DataTalksClub/data-engineering-zoomcamp", "DataTalksClub"),
        ("Data Science", "freeCodeCamp Data Analysis with Python", "https://www.freecodecamp.org/learn/data-analysis-with-python/", "freeCodeCamp"),
        ("Cyber Security", "Cybersecurity Roadmap & Fundamental Labs", "https://roadmap.sh/cyber-security", "roadmap.sh"),
        ("Testing", "Pytest Official Guide & Best Practices", "https://docs.pytest.org/en/stable/getting-started.html", "pytest.org"),
        ("Tailwind CSS", "Tailwind CSS Official Documentation", "https://tailwindcss.com/docs/utility-first", "TailwindCSS"),
        ("Redux", "Redux Essentials Tutorial", "https://redux.js.org/tutorials/essentials/part-1-overview-concepts", "Redux.js"),
        ("Vue.js", "Vue.js Official Tutorial", "https://vuejs.org/tutorial/", "Vue.js"),
        ("Angular", "Angular Official Essentials Guide", "https://angular.dev/overview", "Angular"),
        ("Spring Boot", "Building an Application with Spring Boot", "https://spring.io/guides/gs/spring-boot/", "Spring.io"),
        ("REST APIs", "MDN RESTful Web API Design & HTTP", "https://developer.mozilla.org/en-US/docs/Glossary/REST", "MDN"),
    ]
    for name, title, url, provider in catalog:
        skill = db.scalar(select(Skill).where(func.lower(Skill.name) == name.lower()))
        if not skill:
            skill = Skill(name=name, category="tech")
            db.add(skill)
            db.flush()
        if not db.scalar(
            select(LearningResource.id).where(
                LearningResource.skill_id == skill.id, LearningResource.url == url
            )
        ):
            db.add(LearningResource(skill_id=skill.id, title=title, url=url, provider=provider))
    db.flush()


def market_insights(db: Session, force=False) -> dict:
    now = utcnow()
    cached = db.get(InsightCache, "market")
    if not force and cached and cached.expires_at.replace(tzinfo=timezone.utc) > now:
        return cached.data
    jobs = db.scalars(visible_jobs()).all()
    skills = Counter(s.name for j in jobs for s in j.skills)
    salary_groups = defaultdict(list)
    for j in jobs:
        if j.salary_min is not None and j.salary_max is not None and j.salary_currency and j.salary_interval:
            salary_groups[(j.title, j.location, j.salary_currency, j.salary_interval)].append(
                (j.salary_min + j.salary_max) / 2
            )
    company_counts = Counter(j.company for j in jobs)
    top_10 = company_counts.most_common(10)
    top_10_names = {c[0] for c in top_10}
    others = sum(count for company, count in company_counts.items() if company not in top_10_names)
    capped_companies = dict(top_10)
    if others > 0:
        capped_companies["Others"] = others

    loc_counts = Counter(j.location for j in jobs if j.location and j.location != "Not specified")
    data = {
        "active_jobs": len(jobs),
        "skills": dict(skills.most_common(30)),
        "companies": capped_companies,
        "locations": dict(loc_counts.most_common(10)),
        "types": dict(Counter(j.employment_type for j in jobs)),
        "salaries": [
            {
                "role": key[0],
                "location": key[1],
                "currency": key[2],
                "interval": key[3],
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "average": round(sum(values) / len(values), 2),
                "values": values[:500],
            }
            for key, values in salary_groups.items()
        ],
        "generated_at": now.isoformat(),
    }
    day = now.date().isoformat()
    snapshot = db.get(InsightSnapshot, day) or InsightSnapshot(day=day)
    snapshot.data = {"skills": dict(skills), "active_jobs": len(jobs)}
    db.add(snapshot)
    db.flush()
    data["history"] = [
        {"day": r.day, **r.data}
        for r in db.scalars(select(InsightSnapshot).order_by(InsightSnapshot.day.desc()).limit(90)).all()
    ][::-1]
    cached = cached or InsightCache(key="market")
    cached.data, cached.expires_at = data, now + timedelta(seconds=get_settings().insight_cache_seconds)
    db.add(cached)
    db.commit()
    return data
