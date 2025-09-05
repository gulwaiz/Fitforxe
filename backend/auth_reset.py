import os
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from bson import ObjectId

from deps import get_db  # <-- change to your real path (e.g., from .db import get_db)

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET_KEY = os.getenv("SECRET_KEY", "replace-me")
ALGORITHM = "HS256"
RESET_TOKEN_MINUTES = 30

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

class RequestResetIn(BaseModel):
    email: EmailStr
    gym_name: str

class DoResetIn(BaseModel):
    token: str
    new_password: str

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
            raise HTTPException(400, "Invalid token type")
        return data["sub"]
    except JWTError:
        raise HTTPException(400, "Invalid or expired token")

@router.post("/request-reset")
async def request_reset(body: RequestResetIn, db=Depends(get_db)):
    owner = await db.gym_owners.find_one({
        "email": body.email.lower().strip(),
        "gym_name": body.gym_name.strip(),
    })
    # Always 200 to avoid account enumeration
    if owner:
        token = create_reset_token(owner["_id"])
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={token}"

        # TODO: send email here. For dev we return the link:
        return {"ok": True, "reset_url": reset_url}

    return {"ok": True}

@router.post("/reset")
async def perform_reset(body: DoResetIn, db=Depends(get_db)):
    owner_id = decode_reset_token(body.token)
    result = await db.gym_owners.update_one(
        {"_id": ObjectId(owner_id)},
        {"$set": {
            "password_hash": pwd.hash(body.new_password),
            "password_changed_at": datetime.utcnow()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(400, "Could not reset password")
    return {"ok": True}
