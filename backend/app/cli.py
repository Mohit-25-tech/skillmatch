"""Administrative CLI tools for SkillMatch AI."""

import argparse
import sys
from app.db import SessionLocal
from app.services.enrichment import reembed_all


def main():
    parser = argparse.ArgumentParser(description="SkillMatch AI Admin CLI")
    subparsers = parser.add_subparsers(dest="command")

    reembed_parser = subparsers.add_parser("re-embed", help="Re-embed all jobs and resumes with current vector backend")
    rebuild_parser = subparsers.add_parser("rebuild-vectorstore", help="Rebuild vector store collections from Postgres")
    seed_parser = subparsers.add_parser("seed-resources", help="Seed curated free learning resources and ensure taxonomy skills")

    args = parser.parse_args()
    if args.command in ("re-embed", "rebuild-vectorstore"):
        with SessionLocal() as db:
            print("Starting re-embedding and vector store rebuild...")
            res = reembed_all(db)
            print(f"Operation complete: {res}")
    elif args.command == "seed-resources":
        from app.services.product import seed_resources
        from app.services.taxonomy import ensure_taxonomy
        with SessionLocal() as db:
            print("Ensuring taxonomy...")
            ensure_taxonomy(db)
            print("Seeding curated learning resources...")
            seed_resources(db)
            db.commit()
            print("Curated learning resources seeded successfully.")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
