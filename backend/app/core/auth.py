"""Authentication dependencies for route protection."""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from jose import JWTError

from app.core.database import get_db
from app.core.jwt import decode_token
from app.models.user import User


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract Bearer token from Authorization header. Supports both:
    - JWT access tokens (decoded to get user_id)
    - Legacy UUID session tokens (looked up by session_token column)
    Returns 401 if no valid token is provided.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")

    # Try JWT decode first
    try:
        payload = decode_token(token)
        if payload.get("type") == "access":
            user_id = int(payload["sub"])
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            if not user.is_active:
                raise HTTPException(status_code=401, detail="User account is inactive")
            return user
    except JWTError:
        pass

    # Fall back to session token lookup (legacy)
    user = db.query(User).filter(User.session_token == token).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")

    return user
