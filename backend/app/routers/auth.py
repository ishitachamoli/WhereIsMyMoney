"""Authentication endpoints for email+password and session-based auth."""
import uuid
import logging
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.models.user import User
from pydantic import BaseModel
from jose import JWTError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def hash_password(password: str) -> str:
    """Hash password using bcrypt, truncating to 72 bytes to avoid ValueError."""
    password_bytes = password.encode('utf-8')[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash, truncating to 72 bytes."""
    password_bytes = password.encode('utf-8')[:72]
    return bcrypt.checkpw(password_bytes, hashed.encode('utf-8'))


# ─── Request/Response Schemas ──────────────────────────────────────────────────


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    session_token: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    id: int
    email: Optional[str] = None
    name: str
    is_registered: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserInfo

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str


class SessionRequest(BaseModel):
    token: Optional[str] = None


class SessionResponse(BaseModel):
    token: str
    user_id: int
    name: str

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user_id: int
    name: str
    email: Optional[str] = None
    is_active: bool
    is_registered: bool

    model_config = {"from_attributes": True}


# ─── Registration ──────────────────────────────────────────────────────────────


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email+password.
    If session_token is provided, upgrades the existing session user to a registered account.
    """
    if not body.email or not body.email.strip():
        raise HTTPException(status_code=400, detail="Email is required")
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    email = body.email.strip().lower()

    existing = db.query(User).filter(User.email == email, User.is_registered == True).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = hash_password(body.password)

    if body.session_token:
        user = db.query(User).filter(User.session_token == body.session_token).first()
        if user:
            user.email = email
            user.password_hash = hashed
            user.is_registered = True
            if body.name:
                user.name = body.name
            db.commit()
            db.refresh(user)
            return _build_auth_response(user)

    user = User(
        email=email,
        name=body.name or email.split("@")[0],
        password_hash=hashed,
        is_registered=True,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Registered new user: id={user.id}, email={email}")
    return _build_auth_response(user)


# ─── Login ─────────────────────────────────────────────────────────────────────


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email+password. Returns access and refresh tokens."""
    if not body.email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email, User.is_registered == True).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is inactive")

    return _build_auth_response(user)


# ─── Token Refresh ─────────────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    try:
        payload = decode_token(body.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token(user.id)
    return TokenResponse(access_token=access_token)


# ─── Legacy Session Endpoints ──────────────────────────────────────────────────


@router.post("/session", response_model=SessionResponse)
def create_or_validate_session(
    body: SessionRequest,
    db: Session = Depends(get_db),
):
    """
    Create or validate a session (legacy endpoint).
    - If no token provided: creates a new user + generates a UUID session token.
    - If token provided: validates it and returns the user.
    """
    if body.token:
        user = db.query(User).filter(User.session_token == body.token).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session token")
        return SessionResponse(token=user.session_token, user_id=user.id, name=user.name)

    token = str(uuid.uuid4())
    user_count = db.query(User).count()
    user = User(
        email=f"session-{token[:8]}@wimm.local",
        name=f"User {user_count + 1}",
        session_token=token,
        is_active=True,
        is_registered=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"Created new session user: id={user.id}, token={token[:8]}...")
    return SessionResponse(token=user.session_token, user_id=user.id, name=user.name)


@router.get("/me", response_model=MeResponse)
def get_me(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Return current user info given a Bearer token (JWT or session token)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user = _resolve_user_from_token(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    return MeResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        is_active=user.is_active,
        is_registered=user.is_registered or False,
    )


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _build_auth_response(user: User) -> AuthResponse:
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserInfo(
            id=user.id,
            email=user.email,
            name=user.name,
            is_registered=user.is_registered or False,
        ),
    )


def _resolve_user_from_token(token: str, db: Session) -> Optional[User]:
    """Try JWT decode first, then fall back to session token lookup."""
    try:
        payload = decode_token(token)
        if payload.get("type") == "access":
            user_id = int(payload["sub"])
            return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    except JWTError:
        pass

    # Fall back to session token lookup (legacy)
    return db.query(User).filter(User.session_token == token, User.is_active == True).first()
