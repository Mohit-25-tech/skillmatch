"""Create a platform administrator through a trusted local terminal."""

import getpass

from pydantic import TypeAdapter
from pydantic.networks import EmailStr
from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import password_hash


def main() -> None:
    email = str(TypeAdapter(EmailStr).validate_python(input("Admin email: ").strip())).lower()
    name = input("Display name: ").strip()
    password = getpass.getpass("Password (at least 12 characters): ")
    if len(password) < 12 or len(password) > 128 or len(name) < 2:
        raise SystemExit("Use a 12–128 character password and a name with at least two characters.")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords did not match.")
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit("That email already exists; no account was modified.")
        db.add(User(name=name, email=email, password_hash=password_hash.hash(password), role="admin"))
        db.commit()
    print("Administrator created.")


if __name__ == "__main__":
    main()
