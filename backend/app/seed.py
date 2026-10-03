import argparse
import secrets

from sqlalchemy import func, select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Job, Skill, User
from app.security import password_hash
from app.seed_data import generate_jobs
from app.services.taxonomy import ensure_taxonomy


def seed(demo: bool = False) -> None:
    with SessionLocal() as db:
        ensure_taxonomy(db)
        from app.services.product import seed_resources

        seed_resources(db)
        db.commit()
        if not demo or db.scalar(select(func.count(Job.id)).where(Job.is_demo.is_(True))) > 0:
            return
        owner = db.scalar(select(User).where(User.email == "catalog@skillmatch.example"))
        if not owner:
            owner = User(
                name="SkillMatch Catalog",
                email="catalog@skillmatch.example",
                role="recruiter",
                active=False,
                password_hash=password_hash.hash(secrets.token_urlsafe(32)),
            )
            db.add(owner)
            db.flush()
        skills = {s.name: s for s in db.scalars(select(Skill)).all()}
        for data in generate_jobs():
            names = data.pop("skills")
            db.add(
                Job(
                    **data,
                    recruiter_id=owner.id,
                    is_demo=True,
                    source="demo",
                    salary_currency="USD",
                    salary_interval="year",
                    skills=[skills[n] for n in names],
                )
            )
        db.commit()
        print("Seeded 200 synthetic jobs and 300 skills. No demo credentials were created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-enabled", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    if args.demo and get_settings().environment == "production":
        parser.error("Demo seed is disabled in production")
    if not args.if_enabled or get_settings().seed_on_start:
        seed(demo=args.demo)
