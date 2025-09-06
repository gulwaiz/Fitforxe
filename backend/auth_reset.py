# backend/auth_reset.py
import os, secrets, hashlib
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from bson import ObjectId

# If deps.py is in the SAME folder as this file, this absolute import is correct:
from deps import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY")           # set in Render → Environment
ALGORITHM = "HS256"
RESET_TOKEN_MINUTES = 20
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RequestResetIn(BaseModel):
    gym_name: str
    email: EmailStr

class DoResetIn(BaseModel):
    token: str
    new_password: str

def _now():
    return datetime.now(timezone.utc)

def _new_jti():
    return secrets.token_urlsafe(24)

async def _save_reset_record(db, owner_id: str, jti: str, expires_at: datetime):
    await db.password_resets.insert_one({
        "owner_id": ObjectId(owner_id),
        "jti": jti,
        "expires_at": expires_at,
        "used": False,
        "created_at": _now(),
    })

async def _mark_used(db, jti: str):
    await db.password_resets.update_one(
        {"jti": jti, "used": False}, {"$set": {"used": True, "used_at": _now()}}
    )

async def _is_valid_jti(db, jti: str) -> bool:
    rec = await db.password_resets.find_one({"jti": jti, "used": False})
    return bool(rec and rec["expires_at"] > _now())

def create_reset_token(owner_id: str, jti: str) -> str:
    payload = {
        "sub": str(owner_id),
        "jti": jti,
        "typ": "pwd_reset",
        "exp": _now() + timedelta(minutes=RESET_TOKEN_MINUTES),
        "iat": _now(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_reset_token(token: str):
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("typ") != "pwd_reset":
            raise HTTPException(400, "Invalid token type")
        return data
    except JWTError:
        raise HTTPException(400, "Invalid or expired token")

@router.post("/request-reset")
async def request_reset(body: RequestResetIn, db=Depends(get_db)):
    owner = await db.gym_owners.find_one({
        "email": body.email.lower().strip(),
        "gym_name": body.gym_name.strip(),
    })

    # Always return 200 (don’t leak whether an account exists)
    if owner:
        jti = _new_jti()
        expires_at = _now() + timedelta(minutes=RESET_TOKEN_MINUTES)
        await _save_reset_record(db, owner["_id"], jti, expires_at)

        token = create_reset_token(str(owner["_id"]), jti)
        frontend = os.getenv("FRONTEND_URL", "http://localhost:3000")
        link = f"{frontend}/reset-password?token={token}"

        # DEV HELPER: echo link in response when enabled
        if os.getenv("SHOW_RESET_URL_IN_RESPONSE", "false").lower() == "true":
            return {"ok": True, "reset_url": link}

        # TODO: send email via provider (see emailer.py)
        print("[DEV] Reset URL:", link)

    return {"ok": True}

@router.post("/reset")
async def perform_reset(body: DoResetIn, db=Depends(get_db)):
    data = decode_reset_token(body.token)
    owner_id = data["sub"]
    jti = data["jti"]

    if not await _is_valid_jti(db, jti):
        raise HTTPException(400, "This reset link is no longer valid")

    res = await db.gym_owners.update_one(
        {"_id": ObjectId(owner_id)},
        {"$set": {"password_hash": pwd.hash(body.new_password),
                  "password_changed_at": _now()}}
    )
    if res.matched_count == 0:
        raise HTTPException(400, "Account not found")

    await _mark_used(db, jti)
    return {"ok": True}
