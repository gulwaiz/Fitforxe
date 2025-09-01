from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from jose import jwt, JWTError
from passlib.hash import bcrypt
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from enum import Enum
import uuid
import os
import logging

# -------------------- Load env --------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# -------------------- Config ----------------------
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SECRET_KEY = os.environ.get("JWT_SECRET", "change-me-in-prod")
ALGORITHM = "HS256"
RAW_EXP = os.environ.get("ACCESS_TOKEN_EXPIRES_MINUTES", "0").strip()
ACCESS_TOKEN_EXPIRES_MINUTES: Optional[int] = None if RAW_EXP in ("", "0", "false", "False", "NONE", "None") else int(RAW_EXP)

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY")
if not STRIPE_API_KEY:
    logging.warning("STRIPE_API_KEY not set (Stripe endpoints will error).")

import stripe as stripe_sdk
if STRIPE_API_KEY:
    stripe_sdk.api_key = STRIPE_API_KEY

import razorpay
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET")
razorpay_client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    try:
        razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
    except Exception as e:
        logging.warning(f"Razorpay init failed: {e}")

# -------------------- DB -------------------------
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# -------------------- FastAPI --------------------
app = FastAPI()
api = APIRouter(prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# -------------------- Enums ----------------------
class MembershipType(str, Enum):
    BASIC = "basic"
    PREMIUM = "premium"
    VIP = "vip"

class MemberStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    SUSPENDED = "suspended"

class PaymentStatus(str, Enum):
    PAID = "paid"
    PENDING = "pending"
    OVERDUE = "overdue"
    FAILED = "failed"

class PaymentTransactionStatus(str, Enum):
    INITIATED = "initiated"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"

class PaymentMethodType(str, Enum):
    CASH = "cash"
    STRIPE = "stripe"
    RAZORPAY = "razorpay"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"

# -------------------- Models ---------------------
class GymOwnerCreate(BaseModel):
    email: EmailStr
    password: str
    gym_name: str

class GymOwnerOut(BaseModel):
    id: str
    email: EmailStr
    gym_name: str
    created_at: datetime

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None

class GymOwnerProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    gym_name: str = "FitForce"
    owner_name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    zip_code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class GymOwnerProfileCreate(BaseModel):
    gym_name: Optional[str] = "FitForce"
    owner_name: str
    email: str
    phone: str
    address: str
    city: str
    state: str
    zip_code: str

class GymOwnerProfileUpdate(BaseModel):
    gym_name: Optional[str] = None
    owner_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None

class Member(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: Optional[datetime] = None
    membership_type: MembershipType
    membership_start_date: datetime
    membership_end_date: datetime
    status: MemberStatus = MemberStatus.ACTIVE
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    auto_billing_enabled: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class MemberCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    date_of_birth: Optional[datetime] = None
    membership_type: MembershipType
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: Optional[str] = None
    enable_auto_billing: bool = False

class MemberUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    membership_type: Optional[MembershipType] = None
    status: Optional[MemberStatus] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: Optional[str] = None
    auto_billing_enabled: Optional[bool] = None

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    member_id: str
    amount: float
    payment_date: datetime
    payment_method: str
    status: PaymentStatus
    membership_type: MembershipType
    period_start: datetime
    period_end: datetime
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentCreate(BaseModel):
    member_id: str
    amount: float
    payment_method: str
    membership_type: MembershipType
    notes: Optional[str] = None

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    member_id: str
    session_id: Optional[str] = None
    payment_id: Optional[str] = None
    amount: float
    currency: str = "usd"
    payment_method: PaymentMethodType
    status: PaymentTransactionStatus
    membership_type: MembershipType
    metadata: Optional[Dict[str, str]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RazorpayOrderRequest(BaseModel):
    member_id: str
    membership_type: MembershipType
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_country: str

class PaymentGatewayResponse(BaseModel):
    gateway: str
    payment_url: Optional[str] = None
    order_id: Optional[str] = None
    amount: float
    currency: str
    razorpay_key_id: Optional[str] = None

class Attendance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    member_id: str
    check_in_time: datetime
    check_out_time: Optional[datetime] = None
    date: datetime = Field(default_factory=lambda: datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AttendanceCreate(BaseModel):
    member_id: str

class DashboardStats(BaseModel):
    total_members: int
    active_members: int
    monthly_revenue: float
    pending_payments: int
    todays_checkins: int

# -------------------- Pricing --------------------
MEMBERSHIP_PRICING = {
    MembershipType.BASIC: 29.99,
    MembershipType.PREMIUM: 49.99,
    MembershipType.VIP: 79.99,
}

# -------------------- Auth helpers ----------------
def create_access_token(subject_email: str, owner_id: str) -> str:
    jti = str(uuid.uuid4())
    payload = {"sub": subject_email, "owner_id": owner_id, "jti": jti, "iat": int(datetime.utcnow().timestamp())}
    if ACCESS_TOKEN_EXPIRES_MINUTES is not None:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)
        payload["exp"] = expire
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # ---- Blacklist check (logout support) ----
        jti = payload.get("jti")
        if jti and await db.token_blacklist.find_one({"jti": jti}):
            raise HTTPException(status_code=401, detail="Token revoked")

        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.gym_owners.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# -------------------- AUTH routes -----------------
@api.post("/auth/register", response_model=GymOwnerOut)
async def register_owner(data: GymOwnerCreate):
    existing = await db.gym_owners.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    owner = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "password_hash": bcrypt.hash(data.password),
        "gym_name": data.gym_name,
        "created_at": datetime.utcnow(),
    }
    await db.gym_owners.insert_one(owner)
    return GymOwnerOut(id=owner["id"], email=owner["email"], gym_name=owner["gym_name"], created_at=owner["created_at"])

@api.post("/auth/login", response_model=TokenOut)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await db.gym_owners.find_one({"email": form.username})
    # take gym name from first scope (we send it from the frontend)
    gym_from_form = form.scopes[0] if form.scopes else None

    if (
        not user
        or not bcrypt.verify(form.password, user["password_hash"])
        or (gym_from_form and gym_from_form != user["gym_name"])
    ):
        raise HTTPException(status_code=400, detail="Incorrect email, password, or gym name")

    token = create_access_token(user["email"], user["id"])
    return TokenOut(
        access_token=token,
        expires_in=None if ACCESS_TOKEN_EXPIRES_MINUTES is None else ACCESS_TOKEN_EXPIRES_MINUTES
    )
    
@api.post("/auth/logout")
async def logout(current=Depends(get_current_user), token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if jti:
            await db.token_blacklist.update_one({"jti": jti}, {"$set": {"jti": jti, "revoked_at": datetime.utcnow()}}, upsert=True)
    except JWTError:
        pass
    return {"status": "ok"}

# -------------------- Helpers --------------------
def end_date_from(start: datetime, _type: MembershipType) -> datetime:
    return start + timedelta(days=30)

# -------------------- Profile (per owner) --------
@api.post("/profile", response_model=GymOwnerProfile)
async def create_or_update_profile(body: GymOwnerProfileCreate, current=Depends(get_current_user)):
    owner_id = current["id"]
    existing = await db.gym_owner_profile.find_one({"owner_id": owner_id})
    payload = {**body.dict(), "owner_id": owner_id, "updated_at": datetime.utcnow()}
    if existing:
        await db.gym_owner_profile.update_one({"owner_id": owner_id}, {"$set": payload})
        doc = await db.gym_owner_profile.find_one({"owner_id": owner_id})
        return GymOwnerProfile(**doc)
    else:
        doc = GymOwnerProfile(owner_id=owner_id, **body.dict())
        await db.gym_owner_profile.insert_one(doc.dict())
        return doc

@api.get("/profile", response_model=GymOwnerProfile)
async def get_profile(current=Depends(get_current_user)):
    owner_id = current["id"]
    doc = await db.gym_owner_profile.find_one({"owner_id": owner_id})
    if not doc:
        return GymOwnerProfile(
            owner_id=owner_id,
            owner_name=current.get("gym_name","Owner"),
            email=current["email"],
            phone="+1-555-0000",
            address="123 Fitness Street",
            city="Gym City",
            state="GY",
            zip_code="12345",
        )
    return GymOwnerProfile(**doc)

@api.put("/profile", response_model=GymOwnerProfile)
async def update_profile(body: GymOwnerProfileUpdate, current=Depends(get_current_user)):
    owner_id = current["id"]
    existing = await db.gym_owner_profile.find_one({"owner_id": owner_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Profile not found")
    update_data = {k: v for k, v in body.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    await db.gym_owner_profile.update_one({"owner_id": owner_id}, {"$set": update_data})
    doc = await db.gym_owner_profile.find_one({"owner_id": owner_id})
    return GymOwnerProfile(**doc)

# -------------------- Members --------------------
@api.post("/members", response_model=Member)
async def create_member(body: MemberCreate, current=Depends(get_current_user)):
    owner_id = current["id"]
    existing = await db.members.find_one({"owner_id": owner_id, "email": body.email})
    if existing:
        raise HTTPException(status_code=400, detail="Member with this email already exists")
    start = datetime.utcnow()
    end = end_date_from(start, body.membership_type)
    data = body.dict()
    enable_auto = data.pop("enable_auto_billing", False)
    member = Member(owner_id=owner_id, membership_start_date=start, membership_end_date=end,
                    auto_billing_enabled=enable_auto, **data)
    await db.members.insert_one(member.dict())
    return member

@api.get("/members", response_model=List[Member])
async def get_members(skip: int = 0, limit: int = 100, status: Optional[MemberStatus] = None, current=Depends(get_current_user)):
    owner_id = current["id"]
    q = {"owner_id": owner_id}
    if status: q["status"] = status
    docs = await db.members.find(q).skip(skip).limit(limit).to_list(limit)
    return [Member(**d) for d in docs]

@api.get("/members/{member_id}", response_model=Member)
async def get_member(member_id: str, current=Depends(get_current_user)):
    owner_id = current["id"]
    m = await db.members.find_one({"owner_id": owner_id, "id": member_id})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return Member(**m)

@api.put("/members/{member_id}", response_model=Member)
async def update_member(member_id: str, body: MemberUpdate, current=Depends(get_current_user)):
    owner_id = current["id"]
    m = await db.members.find_one({"owner_id": owner_id, "id": member_id})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    upd = {k: v for k, v in body.dict().items() if v is not None}
    upd["updated_at"] = datetime.utcnow()
    await db.members.update_one({"owner_id": owner_id, "id": member_id}, {"$set": upd})
    m2 = await db.members.find_one({"owner_id": owner_id, "id": member_id})
    return Member(**m2)

@api.delete("/members/{member_id}")
async def delete_member(member_id: str, current=Depends(get_current_user)):
    owner_id = current["id"]
    m = await db.members.find_one({"owner_id": owner_id, "id": member_id})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.members.delete_one({"owner_id": owner_id, "id": member_id})
    return {"message": "Member deleted successfully"}

# -------------------- Razorpay -------------------
@api.post("/razorpay/create-order", response_model=PaymentGatewayResponse)
async def create_razorpay_order(req: RazorpayOrderRequest, current=Depends(get_current_user)):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    owner_id = current["id"]
    member = await db.members.find_one({"owner_id": owner_id, "id": req.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    amount_usd = MEMBERSHIP_PRICING[req.membership_type]
    amount_inr = amount_usd * 83
    amount_paise = int(amount_inr * 100)

    try:
        order = razorpay_client.order.create({"amount": amount_paise, "currency": "INR", "payment_capture": 1,
                                              "notes": {"member_id": req.member_id, "membership_type": req.membership_type}})
        txn = PaymentTransaction(
            owner_id=owner_id,
            member_id=req.member_id,
            session_id=order["id"],
            amount=amount_inr,
            currency="INR",
            payment_method=PaymentMethodType.RAZORPAY,
            status=PaymentTransactionStatus.INITIATED,
            membership_type=req.membership_type,
            metadata={"gateway": "razorpay"},
        )
        await db.payment_transactions.insert_one(txn.dict())
        return PaymentGatewayResponse(gateway="razorpay", order_id=order["id"], amount=amount_inr, currency="INR",
                                      razorpay_key_id=RAZORPAY_KEY_ID)
    except Exception as e:
        logging.error(f"Razorpay order error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create Razorpay order")

@api.post("/razorpay/verify-payment")
async def verify_razorpay_payment(request: Request, current=Depends(get_current_user)):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    body = await request.json()
    order_id = body.get("razorpay_order_id")
    payment_id = body.get("razorpay_payment_id")
    signature = body.get("razorpay_signature")
    try:
        razorpay_client.utility.verify_payment_signature(
            {"razorpay_order_id": order_id, "razorpay_payment_id": payment_id, "razorpay_signature": signature}
        )
        txn = await db.payment_transactions.find_one({"session_id": order_id})
        if txn and txn["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one({"session_id": order_id}, {"$set": {"status": PaymentTransactionStatus.COMPLETED, "payment_id": payment_id, "updated_at": datetime.utcnow()}})
            pay = Payment(
                owner_id=txn["owner_id"],
                member_id=txn["member_id"],
                amount=txn["amount"],
                payment_date=datetime.utcnow(),
                payment_method="razorpay",
                status=PaymentStatus.PAID,
                membership_type=txn["membership_type"],
                period_start=datetime.utcnow(),
                period_end=end_date_from(datetime.utcnow(), txn["membership_type"]),
                notes="Razorpay verified",
            )
            await db.payments.insert_one(pay.dict())
            await db.members.update_one({"id": txn["member_id"], "owner_id": txn["owner_id"]},
                                        {"$set": {"membership_end_date": pay.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}})
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Razorpay verify error: {e}")
        raise HTTPException(status_code=400, detail="Verification failed")

# -------------------- Stripe ---------------------
class CheckoutSessionRequest(BaseModel):
    member_id: str
    membership_type: MembershipType
    success_url: str
    cancel_url: str

class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str

class CheckoutStatusResponse(BaseModel):
    payment_status: str

@api.post("/stripe/checkout", response_model=CheckoutSessionResponse)
async def stripe_checkout(req: CheckoutSessionRequest, current=Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    owner_id = current["id"]
    member = await db.members.find_one({"owner_id": owner_id, "id": req.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    amount = MEMBERSHIP_PRICING[req.membership_type]

    def _create():
        return stripe_sdk.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {"currency": "usd", "product_data": {"name": f"{req.membership_type.value.capitalize()} Membership"}, "unit_amount": int(amount * 100)},
                "quantity": 1
            }],
            success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=req.cancel_url,
            metadata={"owner_id": owner_id, "member_id": req.member_id, "membership_type": req.membership_type.value},
        )
    import anyio
    sess = await anyio.to_thread.run_sync(_create)

    txn = PaymentTransaction(
        owner_id=owner_id,
        member_id=req.member_id,
        session_id=sess.id,
        amount=amount,
        currency="usd",
        payment_method=PaymentMethodType.STRIPE,
        status=PaymentTransactionStatus.INITIATED,
        membership_type=req.membership_type,
        metadata={"gateway": "stripe"},
    )
    await db.payment_transactions.insert_one(txn.dict())
    return CheckoutSessionResponse(session_id=sess.id, url=sess.url)

@api.get("/stripe/checkout/status/{session_id}", response_model=CheckoutStatusResponse)
async def stripe_status(session_id: str, current=Depends(get_current_user)):
    if not STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    def _retrieve():
        return stripe_sdk.checkout.Session.retrieve(session_id)
    import anyio
    sess = await anyio.to_thread.run_sync(_retrieve)
    status_val = sess.get("payment_status") or sess.get("status") or "unknown"
    if status_val == "paid":
        txn = await db.payment_transactions.find_one({"session_id": session_id})
        if txn and txn["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"status": PaymentTransactionStatus.COMPLETED, "updated_at": datetime.utcnow()}})
            pay = Payment(
                owner_id=txn["owner_id"],
                member_id=txn["member_id"],
                amount=txn["amount"],
                payment_date=datetime.utcnow(),
                payment_method="stripe",
                status=PaymentStatus.PAID,
                membership_type=txn["membership_type"],
                period_start=datetime.utcnow(),
                period_end=end_date_from(datetime.utcnow(), txn["membership_type"]),
                notes="Stripe payment processed",
            )
            await db.payments.insert_one(pay.dict())
            await db.members.update_one({"id": txn["member_id"], "owner_id": txn["owner_id"]},
                                        {"$set": {"membership_end_date": pay.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}})
    return CheckoutStatusResponse(payment_status=status_val)

# -------------------- Payments -------------------
@api.post("/payments", response_model=Payment)
async def create_payment(body: PaymentCreate, current=Depends(get_current_user)):
    owner_id = current["id"]
    member = await db.members.find_one({"owner_id": owner_id, "id": body.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    now = datetime.utcnow()
    period_end = end_date_from(now, body.membership_type)
    pay = Payment(
        owner_id=owner_id,
        member_id=body.member_id,
        amount=body.amount,
        payment_date=now,
        payment_method=body.payment_method,
        status=PaymentStatus.PAID,
        membership_type=body.membership_type,
        period_start=now,
        period_end=period_end,
        notes=body.notes,
    )
    await db.payments.insert_one(pay.dict())
    await db.members.update_one({"id": body.member_id, "owner_id": owner_id},
                                {"$set": {"membership_end_date": period_end, "status": MemberStatus.ACTIVE}})
    return pay

@api.get("/payments", response_model=List[Payment])
async def get_payments(skip: int = 0, limit: int = 100, member_id: Optional[str] = None, current=Depends(get_current_user)):
    owner_id = current["id"]
    q = {"owner_id": owner_id}
    if member_id: q["member_id"] = member_id
    docs = await db.payments.find(q).sort("payment_date", -1).skip(skip).limit(limit).to_list(limit)
    return [Payment(**d) for d in docs]

# -------------------- Attendance -----------------
@api.post("/attendance/checkin", response_model=Attendance)
async def check_in(body: AttendanceCreate, current=Depends(get_current_user)):
    owner_id = current["id"]
    member = await db.members.find_one({"owner_id": owner_id, "id": body.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = await db.attendance.find_one({"owner_id": owner_id, "member_id": body.member_id, "date": today, "check_out_time": None})
    if existing:
        raise HTTPException(status_code=400, detail="Member already checked in today")
    rec = Attendance(owner_id=owner_id, member_id=body.member_id, check_in_time=datetime.utcnow(), date=today)
    await db.attendance.insert_one(rec.dict())
    return rec

@api.post("/attendance/checkout/{member_id}")
async def check_out(member_id: str, current=Depends(get_current_user)):
    owner_id = current["id"]
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rec = await db.attendance.find_one({"owner_id": owner_id, "member_id": member_id, "date": today, "check_out_time": None})
    if not rec:
        raise HTTPException(status_code=404, detail="No active check-in found for today")
    await db.attendance.update_one({"id": rec["id"]}, {"$set": {"check_out_time": datetime.utcnow()}})
    return {"message": "Member checked out successfully"}

@api.get("/attendance", response_model=List[Attendance])
async def list_attendance(skip: int = 0, limit: int = 100, current=Depends(get_current_user)):
    owner_id = current["id"]
    docs = await db.attendance.find({"owner_id": owner_id}).sort("check_in_time", -1).skip(skip).limit(limit).to_list(limit)
    return [Attendance(**d) for d in docs]

# -------------------- Dashboard ------------------
@api.get("/dashboard/stats", response_model=DashboardStats)
async def stats(current=Depends(get_current_user)):
    owner_id = current["id"]
    total = await db.members.count_documents({"owner_id": owner_id})
    active = await db.members.count_documents({"owner_id": owner_id, "status": MemberStatus.ACTIVE})
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    pays = await db.payments.find({"owner_id": owner_id, "payment_date": {"$gte": month_start}, "status": PaymentStatus.PAID}).to_list(1000)
    revenue = sum(p["amount"] for p in pays)
    now = datetime.utcnow()
    expired = await db.members.count_documents({"owner_id": owner_id, "membership_end_date": {"$lt": now}, "status": MemberStatus.ACTIVE})
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays = await db.attendance.count_documents({"owner_id": owner_id, "date": today})
    return DashboardStats(total_members=total, active_members=active, monthly_revenue=revenue, pending_payments=expired, todays_checkins=todays)

# -------------------- Utility --------------------
@api.get("/detect-country")
async def detect_country(request: Request):
    try:
        ip = request.client.host or ""
        if ip.startswith(("127.0.0.", "::1", "192.168.")):
            return {"country": "IN", "country_name": "India"}
        return {"country": "US", "country_name": "United States"}
    except Exception as e:
        logging.error(f"detect-country error: {e}")
        return {"country": "US", "country_name": "United States"}

# -------------------- Register router ------------
app.include_router(api)

# -------------------- Shutdown -------------------
@app.on_event("shutdown")
async def shutdown_db():
    client.close()
