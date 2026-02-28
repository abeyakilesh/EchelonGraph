"""Authentication & Authorization — JWT-based with role access control."""
import os
import time
import hashlib
import hmac
import json
import base64
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer(auto_error=False)

# ── Secret ──────────────────────────────────────────────────
JWT_SECRET = os.getenv("JWT_SECRET", "echelon_jwt_secret_key_2024")
JWT_EXPIRY = 86400  # 24 hours

# ── In-memory user store ────────────────────────────────────
def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

USERS = {
    "admin": {"password": _hash("echelon123"), "role": "admin", "name": "Admin User"},
    "investigator": {"password": _hash("investigate123"), "role": "investigator", "name": "Lead Investigator"},
    "auditor": {"password": _hash("audit123"), "role": "auditor", "name": "Compliance Auditor"},
    "viewer": {"password": _hash("view123"), "role": "viewer", "name": "Read-Only Viewer"},
}

# ── Audit log ───────────────────────────────────────────────
audit_log: list = []

def log_action(user: str, action: str, target: str = ""):
    audit_log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "action": action,
        "target": target,
    })
    if len(audit_log) > 5000:
        audit_log.pop(0)

# ── JWT helpers ─────────────────────────────────────────────
def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _b64d(s: str) -> bytes:
    pad = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * pad)

def create_token(username: str, role: str) -> str:
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps({
        "sub": username, "role": role,
        "iat": int(time.time()), "exp": int(time.time()) + JWT_EXPIRY
    }).encode())
    sig = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"

def verify_token(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header, payload, sig = parts
        expected = _b64(hmac.new(JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(_b64d(payload))
        if data.get("exp", 0) < time.time():
            return None
        return data
    except Exception:
        return None

# ── Dependencies ────────────────────────────────────────────
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

async def require_role(*roles):
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return checker

# ── Models ──────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    token: str
    user: dict

# ── Endpoints ───────────────────────────────────────────────
@router.post("/login")
async def login(req: LoginRequest):
    user = USERS.get(req.username)
    if not user or user["password"] != _hash(req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(req.username, user["role"])
    log_action(req.username, "LOGIN")
    return {
        "token": token,
        "user": {
            "username": req.username,
            "name": user["name"],
            "role": user["role"],
        }
    }

@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    stored = USERS.get(user["sub"], {})
    return {
        "username": user["sub"],
        "role": user["role"],
        "name": stored.get("name", user["sub"]),
    }

@router.get("/audit-log")
async def get_audit_log(user=Depends(get_current_user), limit: int = 100):
    if user["role"] not in ("admin", "auditor"):
        raise HTTPException(status_code=403, detail="Admin or auditor access required")
    return {"entries": audit_log[-limit:], "total": len(audit_log)}

@router.get("/users")
async def list_users(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return {
        "users": [
            {"username": u, "name": d["name"], "role": d["role"]}
            for u, d in USERS.items()
        ]
    }
