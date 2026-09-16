import hashlib
import secrets
import time

import jwt
from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select, update

from backend.cache import cache
from backend.config import settings
from backend.db import Session
from backend.errors import DomainError
from backend.models import RefreshToken, User
from backend.repositories import required

bearer = HTTPBearer(auto_error=False)
passwords = PasswordHash.recommended()


def public_user(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def issue_tokens(db, user: User, response: Response) -> dict:
    now = time.time()
    access = jwt.encode(
        {
            "sub": user.id,
            "type": "access",
            "iat": now,
            "exp": now + 900,
            "iss": "shopilot",
            "aud": "shopilot-ui",
        },
        settings().jwt_secret,
        algorithm="HS256",
    )
    refresh = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id, digest=hashlib.sha256(refresh.encode()).hexdigest(), expires_at=now + 7 * 86400
        )
    )
    response.set_cookie(
        "shopilot_refresh",
        refresh,
        httponly=True,
        samesite="strict",
        secure=settings().app_env == "production",
        max_age=7 * 86400,
        path="/api/auth",
    )
    cache.set(f"session:{user.id}", {"last_login": now}, 900)
    return {"access_token": access, "token_type": "bearer", "user": public_user(user)}


DUMMY_HASH = passwords.hash("unusable-login-timing-placeholder")


def login(email: str, password: str, response: Response):
    with Session.begin() as db:
        user = db.scalar(select(User).where(User.email == email.lower()))
        valid = passwords.verify(password, user.password_hash if user else DUMMY_HASH)
        if not user or not valid:
            raise DomainError("Email or password is incorrect.", 401, "invalid_credentials")
        return issue_tokens(db, user, response)


def refresh(request: Request, response: Response):
    raw = request.cookies.get("shopilot_refresh", "")
    digest = hashlib.sha256(raw.encode()).hexdigest()
    with Session.begin() as db:
        token = db.scalar(select(RefreshToken).where(RefreshToken.digest == digest))
        if not token or token.revoked or token.expires_at < time.time():
            raise DomainError("Please sign in again.", 401, "expired_session")
        changed = db.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token.id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        if getattr(changed, "rowcount", 0) != 1:
            raise DomainError("Refresh token already used.", 401)
        return issue_tokens(db, required(db, User, token.user_id), response)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if not credentials:
        raise DomainError("Sign in to continue.", 401, "unauthenticated")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings().jwt_secret,
            algorithms=["HS256"],
            audience="shopilot-ui",
            issuer="shopilot",
            options={"require": ["sub", "exp", "type"]},
        )
        if payload["type"] != "access":
            raise jwt.InvalidTokenError()
    except jwt.PyJWTError:
        raise DomainError("Session expired. Please sign in again.", 401, "unauthenticated") from None
    with Session() as db:
        user = required(db, User, payload["sub"])
        if not user:
            raise DomainError("Account not found.", 401)
        return user


def require_roles(*roles: str):
    def dependency(user: User = Depends(current_user)):
        if user.role not in roles:
            raise DomainError("Your role cannot perform this action.", 403, "forbidden")
        return user

    return dependency
