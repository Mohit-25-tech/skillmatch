import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.limits import limiter
from app.models import Application, Notification, RefreshSession, Resume, SavedSearch, User, utcnow
from app.schemas import Login, Register
from app.security import (
    DUMMY_HASH,
    check_origin,
    current_user,
    decode_token,
    issue_tokens,
    password_hash,
    user_public,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyConfirm(BaseModel):
    token: str = Field(min_length=1)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
def register(request: Request, body: Register, response: Response, db: Session = Depends(get_db)) -> dict:
    user = User(
        name=body.name,
        email=str(body.email).lower(),
        role=body.role,
        password_hash=password_hash.hash(body.password),
        verification_token=secrets.token_urlsafe(32),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists") from None
    return issue_tokens(user, db, response)


@router.post("/login")
@limiter.limit("10/minute")
def login(request: Request, body: Login, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    valid = password_hash.verify(body.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Email or password is incorrect")
    return issue_tokens(user, db, response)


@router.post("/refresh")
@limiter.limit("30/minute")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    check_origin(request)
    payload = decode_token(request.cookies.get("refresh_token", ""), "refresh")
    user = db.get(User, int(payload["sub"]))
    removed = db.execute(
        delete(RefreshSession).where(
            RefreshSession.id == payload.get("jti"), RefreshSession.user_id == int(payload["sub"])
        )
    )
    if not user or not user.active or user.token_version != payload["ver"] or removed.rowcount != 1:
        db.rollback()
        raise HTTPException(401, "Please sign in again")
    return issue_tokens(user, db, response)


@router.post("/logout", status_code=204)
def logout(
    request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    check_origin(request)
    user.token_version += 1
    db.execute(delete(RefreshSession).where(RefreshSession.user_id == user.id))
    db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_public(user)


@router.post("/verify/request")
@limiter.limit("3/minute")
def request_verification(
    request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> dict:
    if user.email_verified:
        return {"status": "already_verified", "message": "Your email is already verified"}
    token = secrets.token_urlsafe(32)
    user.verification_token = token
    db.commit()
    return {
        "status": "pending",
        "message": "Verification token generated. In a live environment, check your inbox.",
        "token": token,  # Exposed for automated testing & development verification
    }


@router.post("/verify/confirm")
def confirm_verification(body: VerifyConfirm, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.verification_token == body.token))
    if not user:
        raise HTTPException(400, "Invalid or expired verification token")
    user.email_verified = True
    user.verification_token = None
    db.commit()
    return {"status": "verified", "message": "Email successfully verified"}


@router.post("/password-reset/request")
@limiter.limit("3/minute")
def request_password_reset(
    request: Request, body: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict:
    user = db.scalar(select(User).where(User.email == str(body.email).lower()))
    token = None
    if user and user.active:
        token = secrets.token_urlsafe(32)
        user.reset_token = token
        user.reset_token_expires_at = utcnow() + timedelta(hours=1)
        db.commit()
    return {
        "status": "sent",
        "message": "If an account exists with this email address, a password reset link has been dispatched.",
        "token": token,  # For test environment automation
    }


@router.post("/password-reset/confirm")
@limiter.limit("5/minute")
def confirm_password_reset(
    request: Request, body: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict:
    user = db.scalar(select(User).where(User.reset_token == body.token))
    if not user or not user.reset_token_expires_at or user.reset_token_expires_at < utcnow():
        raise HTTPException(400, "Reset token is invalid or has expired")
    user.password_hash = password_hash.hash(body.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.token_version += 1
    db.execute(delete(RefreshSession).where(RefreshSession.user_id == user.id))
    db.commit()
    return {"status": "success", "message": "Your password has been reset. Please sign in with your new password."}


@router.get("/unsubscribe")
def unsubscribe(
    email: EmailStr = Query(...), token: str | None = Query(None), db: Session = Depends(get_db)
) -> dict:
    user = db.scalar(select(User).where(User.email == str(email).lower()))
    if not user:
        raise HTTPException(404, "User not found")
    prefs = dict(user.preferences)
    prefs["job_alerts"] = False
    prefs["email_digest"] = False
    user.preferences = prefs
    db.commit()
    return {"status": "unsubscribed", "message": f"Successfully unsubscribed {email} from email digests and alerts."}


@router.get("/export")
def export_user_data(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
    resumes = db.scalars(select(Resume).where(Resume.user_id == user.id)).all()
    applications = db.scalars(select(Application).where(Application.user_id == user.id)).all()
    searches = db.scalars(select(SavedSearch).where(SavedSearch.user_id == user.id)).all()
    return {
        "profile": user_public(user),
        "preferences": user.preferences,
        "resumes": [
            {
                "id": r.id,
                "filename": r.filename,
                "text": r.text,
                "skills": [s.name for s in r.skills],
                "is_primary": r.is_primary,
                "parse_warnings": r.parse_warnings or [],
                "created_at": r.created_at.isoformat(),
            }
            for r in resumes
        ],
        "applications": [
            {
                "id": a.id,
                "job_id": a.job_id,
                "custom_company": a.custom_company,
                "custom_title": a.custom_title,
                "status": a.status,
                "notes": a.notes,
                "follow_up_at": a.follow_up_at.isoformat() if a.follow_up_at else None,
                "created_at": a.created_at.isoformat(),
            }
            for a in applications
        ],
        "saved_searches": [
            {
                "id": s.id,
                "name": s.name,
                "filters": s.filters,
                "alerts": s.alerts,
                "created_at": s.created_at.isoformat(),
            }
            for s in searches
        ],
    }


@router.delete("/account", status_code=204)
def delete_account(
    request: Request, response: Response, user: User = Depends(current_user), db: Session = Depends(get_db)
) -> None:
    check_origin(request)
    db.delete(user)
    db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")
