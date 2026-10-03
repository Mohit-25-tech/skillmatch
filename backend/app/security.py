from datetime import datetime, timedelta, timezone
from secrets import token_hex

import jwt
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import RefreshSession, User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
settings = get_settings()
DUMMY_HASH = password_hash.hash("dummy-password-for-timing-consistency")


def decode_token(token: str, kind: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience="skillmatch",
            options={"require": ["exp", "sub", "type", "ver"]},
        )
        if payload["type"] != kind:
            raise ValueError("Wrong token type")
        return payload
    except (jwt.PyJWTError, ValueError):
        raise HTTPException(401, "Your session has expired. Please sign in again.") from None


def issue_tokens(user: User, db: Session, response: Response) -> dict:
    now = datetime.now(timezone.utc)
    db.execute(delete(RefreshSession).where(RefreshSession.expires_at < now))
    common = {"sub": str(user.id), "ver": user.token_version, "aud": "skillmatch", "iat": now}
    access = jwt.encode(
        {**common, "type": "access", "exp": now + timedelta(minutes=15)},
        settings.jwt_secret,
        algorithm="HS256",
    )
    jti = token_hex(32)
    expires = now + timedelta(days=7)
    refresh = jwt.encode(
        {**common, "type": "refresh", "jti": jti, "exp": expires}, settings.jwt_secret, algorithm="HS256"
    )
    db.add(RefreshSession(id=jti, user_id=user.id, expires_at=expires))
    db.commit()
    response.set_cookie(
        "refresh_token",
        refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=604800,
        path="/api/v1/auth",
    )
    return {"access_token": access, "token_type": "bearer", "user": user_public(user)}


def user_public(user: User) -> dict:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "email_verified": getattr(user, "email_verified", False),
    }


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(401, "Please sign in to continue")
    payload = decode_token(credentials.credentials, "access")
    user = db.get(User, int(payload["sub"]))
    if not user or not user.active or user.token_version != payload["ver"]:
        raise HTTPException(401, "Session is no longer valid")
    return user


def roles(*allowed: str):
    def check(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(403, "This action is not available for your role")
        return user

    return check


def check_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    allowed = settings.cors_origins.split(",")
    if origin and origin not in allowed:
        raise HTTPException(403, "Untrusted request origin")


def optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User | None:
    return current_user(credentials, db) if credentials else None
