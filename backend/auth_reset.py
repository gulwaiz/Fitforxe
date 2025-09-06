import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from bson import ObjectId

# If deps.py sits next to this file, this is correct:
from deps import get_db  # <-- adjust only if your path differs

router = APIRouter(prefix="/auth", tags=["auth"])

# -----------------------------
# Config
# -----------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "replace-me")  # <-- set a real secret in Render env
ALGORITHM = "HS256"
RESET_TOKEN_MINUTES = 30
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# -----------------------------
# Models
# -----------------------------
class RequestResetIn(BaseModel):
    email: EmailStr
    gym_name: str

class DoResetIn(BaseModel):
    token: str
    new_password: str

# -----------------------------
# Token helpers
# -----------------------------
def create_reset_token(owner_id: str) -> str:
    payload = {
        "sub": str(owner_id),
        "typ": "pwd_reset",
        "exp": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_reset_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if data.get("typ") != "pwd_reset":
            raise HTTPException(status_code=400, detail="Invalid token type")
        return data["sub"]
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

# -----------------------------
# Endpoints
# -----------------------------
async def _request_reset_impl(body: RequestResetIn, db):
    # Normalize inputs
    email = body.email.lower().strip()
    gym = body.gym_name.strip()

    owner = await db.gym_owners.find_one({"email": email, "gym_name": gym})

    # Always 200 to avoid account enumeration
    if owner:
        token = create_reset_token(owner["_id"])
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"

        # TODO: send the email here.
        # For now we just return the link so you can test quickly.
        # (Once you add an email provider, remove reset_url from the response.)
        return {"ok": True, "reset_url": reset_url}

    return {"ok": True}

@router.post("/request-reset")
async def request_reset(body: RequestResetIn, db=Depends(get_db)):
    return await _request_reset_impl(body, db)

# Alias to match your frontend call /api/auth/forgot-password
@router.post("/forgot-password")
async def forgot_password(body: RequestResetIn, db=Depends(get_db)):
    return await _request_reset_impl(body, db)

async def _perform_reset_impl(body: DoResetIn, db):
    owner_id = decode_reset_token(body.token)
    result = await db.gym_owners.update_one(
        {"_id": ObjectId(owner_id)},
        {
            "$set": {
                "password_hash": pwd.hash(body.new_password),
                "password_changed_at": datetime.utcnow(),
            }
        },
    )
    if result.modified_count == 0:
        # Either the same password hash or user not found
        raise HTTPException(status_code=400, detail="Could not reset password")
    return {"ok": True}

@router.post("/reset")
async def perform_reset(body: DoResetIn, db=Depends(get_db)):
    return await _perform_reset_impl(body, db)

# Alias so /api/auth/reset-password also works
@router.post("/reset-password")
async def perform_reset_alias(body: DoResetIn, db=Depends(get_db)):
    return await _perform_reset_impl(body, db)
