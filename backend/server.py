from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from jose import jwt, JWTError

import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
from enum import Enum

# payments
import stripe, anyio
import razorpay

# =========================
# Env & App Setup
# =========================
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-please")  # set in Render
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "43200"))  # 30 days

# Mongo
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Stripe
stripe_api_key = os.environ.get("STRIPE_API_KEY")
if not stripe_api_key:
    logging.warning("STRIPE_API_KEY not found in environment variables")
stripe.api_key = stripe_api_key

# Razorpay
razorpay_key_id = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_YOUR_KEY_ID")
razorpay_key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "YOUR_KEY_SECRET")
razorpay_client = None
if razorpay_key_id and razorpay_key_secret:
    try:
        razorpay_client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
    except Exception as e:
        logging.warning(f"Razorpay client initialization failed: {e}")
else:
    logging.warning("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not found in environment variables")

# FastAPI
app = FastAPI()
api = APIRouter(prefix="/api")


# =========================
# Auth & Multi-tenant Models
# =========================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    gym_name: str

class UserPublic(BaseModel):
    id: str
    email: EmailStr
    gym_name: str
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def hash_password(p: str) -> str:
    return pwd_context.hash(p)

def verify_password(p: str, hashed: str) -> bool:
    return pwd_context.verify(p, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta and expires_delta.total_seconds() > 0:   # ✅ add this check
        expire = datetime.utcnow() + expires_delta
        to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserPublic:
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid: str = payload.get("sub")
        if uid is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await db.users.find_one({"id": uid})
    if not user:
        raise credentials_exception
    return UserPublic(id=user["id"], email=user["email"], gym_name=user["gym_name"], created_at=user["created_at"])

@api.post("/auth/register", response_model=UserPublic)
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    doc = {
        "id": str(uuid.uuid4()),
        "email": user.email,
        "password_hash": hash_password(user.password),
        "gym_name": user.gym_name,
        "created_at": datetime.utcnow(),
    }
    await db.users.insert_one(doc)
    # create an empty per-owner profile
    await db.gym_owner_profile.update_one(
        {"owner_id": doc["id"]},
        {"$setOnInsert": {
            "id": str(uuid.uuid4()),
            "owner_id": doc["id"],
            "gym_name": user.gym_name,
            "owner_name": "",
            "email": user.email,
            "phone": "",
            "address": "",
            "city": "",
            "state": "",
            "zip_code": "",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )
    return UserPublic(id=doc["id"], email=doc["email"], gym_name=doc["gym_name"], created_at=doc["created_at"])

@api.post("/auth/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form.username})
    if not user or not verify_password(form.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    token = create_access_token({"sub": user["id"]})
    return TokenResponse(access_token=token)

@api.get("/auth/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_user)):
    return current_user


# =========================
# Domain Models (scoped by owner_id)
# =========================
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

class GymOwnerProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner_id: str
    gym_name: str = "FitForce"
    owner_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class GymOwnerProfileCreate(BaseModel):
    gym_name: Optional[str] = None
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


# =========================
# Pricing & Helpers
# =========================
MEMBERSHIP_PRICING = {
    MembershipType.BASIC: 29.99,
    MembershipType.PREMIUM: 49.99,
    MembershipType.VIP: 79.99,
}

def calculate_membership_end_date(start_date: datetime, membership_type: MembershipType) -> datetime:
    return start_date + timedelta(days=30)


# =========================
# Profile (scoped)
# =========================
@api.post("/profile", response_model=GymOwnerProfile)
async def create_or_update_profile(profile_data: GymOwnerProfileCreate, current: UserPublic = Depends(get_current_user)):
    existing = await db.gym_owner_profile.find_one({"owner_id": current.id})
    if existing:
        update = {k: v for k, v in profile_data.dict().items() if v is not None}
        update["updated_at"] = datetime.utcnow()
        await db.gym_owner_profile.update_one({"owner_id": current.id}, {"$set": update})
        fresh = await db.gym_owner_profile.find_one({"owner_id": current.id})
        return GymOwnerProfile(**fresh)
    else:
        doc = GymOwnerProfile(
            owner_id=current.id,
            gym_name=profile_data.gym_name or current.gym_name,
            owner_name=profile_data.owner_name,
            email=profile_data.email,
            phone=profile_data.phone,
            address=profile_data.address,
            city=profile_data.city,
            state=profile_data.state,
            zip_code=profile_data.zip_code,
        )
        await db.gym_owner_profile.insert_one(doc.dict())
        return doc

@api.get("/profile", response_model=GymOwnerProfile)
async def get_profile(current: UserPublic = Depends(get_current_user)):
    profile = await db.gym_owner_profile.find_one({"owner_id": current.id})
    if not profile:
        # create a default on the fly
        doc = GymOwnerProfile(owner_id=current.id, gym_name=current.gym_name, email=current.email)
        await db.gym_owner_profile.insert_one(doc.dict())
        return doc
    return GymOwnerProfile(**profile)


# =========================
# Members (scoped)
# =========================
@api.post("/members", response_model=Member)
async def create_member(member_data: MemberCreate, current: UserPublic = Depends(get_current_user)):
    existing = await db.members.find_one({"owner_id": current.id, "email": member_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Member with this email already exists")

    start_date = datetime.utcnow()
    end_date = calculate_membership_end_date(start_date, member_data.membership_type)
    m = Member(
        owner_id=current.id,
        first_name=member_data.first_name,
        last_name=member_data.last_name,
        email=member_data.email,
        phone=member_data.phone,
        date_of_birth=member_data.date_of_birth,
        membership_type=member_data.membership_type,
        membership_start_date=start_date,
        membership_end_date=end_date,
        status=MemberStatus.ACTIVE,
        emergency_contact_name=member_data.emergency_contact_name,
        emergency_contact_phone=member_data.emergency_contact_phone,
        medical_conditions=member_data.medical_conditions,
        auto_billing_enabled=member_data.enable_auto_billing,
    )
    await db.members.insert_one(m.dict())
    return m

@api.get("/members", response_model=List[Member])
async def get_members(skip: int = 0, limit: int = 100, status: Optional[MemberStatus] = None, current: UserPublic = Depends(get_current_user)):
    q: Dict = {"owner_id": current.id}
    if status:
        q["status"] = status
    items = await db.members.find(q).skip(skip).limit(limit).to_list(limit)
    return [Member(**i) for i in items]

@api.get("/members/{member_id}", response_model=Member)
async def get_member(member_id: str, current: UserPublic = Depends(get_current_user)):
    m = await db.members.find_one({"owner_id": current.id, "id": member_id})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return Member(**m)

@api.put("/members/{member_id}", response_model=Member)
async def update_member(member_id: str, member_update: MemberUpdate, current: UserPublic = Depends(get_current_user)):
    m = await db.members.find_one({"owner_id": current.id, "id": member_id})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    update = {k: v for k, v in member_update.dict().items() if v is not None}
    update["updated_at"] = datetime.utcnow()
    await db.members.update_one({"owner_id": current.id, "id": member_id}, {"$set": update})
    fresh = await db.members.find_one({"owner_id": current.id, "id": member_id})
    return Member(**fresh)

@api.delete("/members/{member_id}")
async def delete_member(member_id: str, current: UserPublic = Depends(get_current_user)):
    m = await db.members.find_one({"owner_id": current.id, "id": member_id})
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.members.delete_one({"owner_id": current.id, "id": member_id})
    return {"message": "Member deleted successfully"}


# =========================
# Razorpay (scoped)
# =========================
@api.post("/razorpay/create-order", response_model=PaymentGatewayResponse)
async def create_razorpay_order(request_body: RazorpayOrderRequest, current: UserPublic = Depends(get_current_user)):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    member = await db.members.find_one({"owner_id": current.id, "id": request_body.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    amount_usd = MEMBERSHIP_PRICING[request_body.membership_type]
    amount_inr = amount_usd * 83
    amount_paise = int(amount_inr * 100)

    try:
        rp_order = razorpay_client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "owner_id": current.id,
                    "member_id": request_body.member_id,
                    "membership_type": request_body.membership_type,
                    "gym_name": current.gym_name,
                    "customer_name": request_body.customer_name,
                    "customer_email": request_body.customer_email,
                },
            }
        )

        txn = PaymentTransaction(
            owner_id=current.id,
            member_id=request_body.member_id,
            session_id=rp_order["id"],
            amount=amount_inr,
            currency="INR",
            payment_method=PaymentMethodType.RAZORPAY,
            status=PaymentTransactionStatus.INITIATED,
            membership_type=request_body.membership_type,
            metadata={
                "gateway": "razorpay",
                "customer_name": request_body.customer_name,
                "customer_email": request_body.customer_email,
                "customer_phone": request_body.customer_phone,
                "customer_country": request_body.customer_country,
            },
        )
        await db.payment_transactions.insert_one(txn.dict())

        return PaymentGatewayResponse(
            gateway="razorpay",
            order_id=rp_order["id"],
            amount=amount_inr,
            currency="INR",
            razorpay_key_id=razorpay_key_id,
        )
    except Exception as e:
        logging.error(f"Razorpay order creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")

@api.post("/razorpay/verify-payment")
async def verify_razorpay_payment(request: Request, current: UserPublic = Depends(get_current_user)):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    try:
        body = await request.json()
        razorpay_order_id = body.get("razorpay_order_id")
        razorpay_payment_id = body.get("razorpay_payment_id")
        razorpay_signature = body.get("razorpay_signature")

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        txn = await db.payment_transactions.find_one({"owner_id": current.id, "session_id": razorpay_order_id})
        if txn and txn["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one(
                {"owner_id": current.id, "session_id": razorpay_order_id},
                {"$set": {"status": PaymentTransactionStatus.COMPLETED, "payment_id": razorpay_payment_id, "updated_at": datetime.utcnow()}},
            )
            payment = Payment(
                owner_id=current.id,
                member_id=txn["member_id"],
                amount=txn["amount"],
                payment_date=datetime.utcnow(),
                payment_method="razorpay",
                status=PaymentStatus.PAID,
                membership_type=txn["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), txn["membership_type"]),
                notes="Razorpay payment verified and processed",
            )
            await db.payments.insert_one(payment.dict())
            await db.members.update_one(
                {"owner_id": current.id, "id": txn["member_id"]},
                {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
            )

        return {"status": "success", "message": "Payment verified successfully"}
    except razorpay.errors.SignatureVerificationError:
        logging.error("Razorpay signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        logging.error(f"Razorpay payment verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment verification failed")

@api.post("/webhook/razorpay")
async def handle_razorpay_webhook(request: Request):
    # Webhooks generally don't have auth token; if you need multi-tenant, embed owner_id in notes and look it up.
    try:
        webhook_data = await request.json()
        event_type = webhook_data.get("event")
        if event_type == "payment.captured":
            payment_data = webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_data.get("order_id")
            payment_id = payment_data.get("id")

            txn = await db.payment_transactions.find_one({"session_id": order_id})
            if txn and txn["status"] != PaymentTransactionStatus.COMPLETED:
                await db.payment_transactions.update_one(
                    {"session_id": order_id},
                    {"$set": {"status": PaymentTransactionStatus.COMPLETED, "payment_id": payment_id, "updated_at": datetime.utcnow()}},
                )
                payment = Payment(
                    owner_id=txn["owner_id"],
                    member_id=txn["member_id"],
                    amount=txn["amount"],
                    payment_date=datetime.utcnow(),
                    payment_method="razorpay",
                    status=PaymentStatus.PAID,
                    membership_type=txn["membership_type"],
                    period_start=datetime.utcnow(),
                    period_end=calculate_membership_end_date(datetime.utcnow(), txn["membership_type"]),
                    notes="Razorpay webhook processed",
                )
                await db.payments.insert_one(payment.dict())
                await db.members.update_one(
                    {"owner_id": txn["owner_id"], "id": txn["member_id"]},
                    {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
                )
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Razorpay webhook processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


# =========================
# Utility
# =========================
@api.get("/detect-country")
async def detect_country(request: Request):
    try:
        client_ip = request.client.host or ""
        if client_ip.startswith(("127.0.0.", "::1", "192.168.")):
            return {"country": "IN", "country_name": "India"}
        return {"country": "US", "country_name": "United States"}
    except Exception as e:
        logging.error(f"Country detection failed: {str(e)}")
        return {"country": "US", "country_name": "United States"}


# =========================
# Stripe (official SDK) — scoped
# =========================
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
async def create_stripe_checkout(request_body: CheckoutSessionRequest, current: UserPublic = Depends(get_current_user)):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    member = await db.members.find_one({"owner_id": current.id, "id": request_body.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    amount = MEMBERSHIP_PRICING[request_body.membership_type]

    def _create():
        return stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"{request_body.membership_type.value.capitalize()} Membership"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            success_url=request_body.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request_body.cancel_url,
            metadata={
                "owner_id": current.id,
                "member_id": request_body.member_id,
                "membership_type": request_body.membership_type.value,
                "gym_name": current.gym_name,
            },
        )

    session = await anyio.to_thread.run_sync(_create)

    txn = PaymentTransaction(
        owner_id=current.id,
        member_id=request_body.member_id,
        session_id=session.id,
        amount=amount,
        currency="usd",
        payment_method=PaymentMethodType.STRIPE,
        status=PaymentTransactionStatus.INITIATED,
        membership_type=request_body.membership_type,
        metadata={"gateway": "stripe"},
    )
    await db.payment_transactions.insert_one(txn.dict())

    return CheckoutSessionResponse(session_id=session.id, url=session.url)

@api.get("/stripe/checkout/status/{session_id}", response_model=CheckoutStatusResponse)
async def get_stripe_checkout_status(session_id: str, current: UserPublic = Depends(get_current_user)):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    def _retrieve():
        return stripe.checkout.Session.retrieve(session_id)

    sess = await anyio.to_thread.run_sync(_retrieve)
    payment_status = sess.get("payment_status") or sess.get("status") or "unknown"

    if payment_status == "paid":
        txn = await db.payment_transactions.find_one({"owner_id": current.id, "session_id": session_id})
        if txn and txn["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one(
                {"owner_id": current.id, "session_id": session_id},
                {"$set": {"status": PaymentTransactionStatus.COMPLETED, "updated_at": datetime.utcnow()}},
            )
            payment = Payment(
                owner_id=current.id,
                member_id=txn["member_id"],
                amount=txn["amount"],
                payment_date=datetime.utcnow(),
                payment_method="stripe",
                status=PaymentStatus.PAID,
                membership_type=txn["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), txn["membership_type"]),
                notes="Stripe payment processed",
            )
            await db.payments.insert_one(payment.dict())
            await db.members.update_one(
                {"owner_id": current.id, "id": txn["member_id"]},
                {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
            )

    return CheckoutStatusResponse(payment_status=payment_status)

@api.post("/webhook/stripe")
async def handle_stripe_webhook(request: Request):
    # Typically unauthenticated; use metadata owner_id to scope
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        def _construct():
            if endpoint_secret:
                return stripe.Webhook.construct_event(payload, sig, endpoint_secret)
            else:
                return stripe.Event.construct_from({"type": "unchecked", "data": {"object": {}}}, stripe.api_key)
        event = await anyio.to_thread.run_sync(_construct)
    except Exception as e:
        logging.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload/signature")

    if event and event.get("type") == "checkout.session.completed":
        sess = event["data"]["object"]
        session_id = sess["id"]
        owner_id = (sess.get("metadata") or {}).get("owner_id")
        txn = await db.payment_transactions.find_one({"session_id": session_id})
        if txn and txn["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"status": PaymentTransactionStatus.COMPLETED, "updated_at": datetime.utcnow()}},
            )
            payment = Payment(
                owner_id=owner_id or txn["owner_id"],
                member_id=txn["member_id"],
                amount=txn["amount"],
                payment_date=datetime.utcnow(),
                payment_method="stripe",
                status=PaymentStatus.PAID,
                membership_type=txn["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), txn["membership_type"]),
                notes="Stripe webhook processed",
            )
            await db.payments.insert_one(payment.dict())
            await db.members.update_one(
                {"owner_id": payment.owner_id, "id": txn["member_id"]},
                {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
            )

    return {"status": "success"}


# =========================
# Payments (manual) — scoped
# =========================
@api.post("/payments", response_model=Payment)
async def create_payment(payment_data: PaymentCreate, current: UserPublic = Depends(get_current_user)):
    member = await db.members.find_one({"owner_id": current.id, "id": payment_data.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    payment_date = datetime.utcnow()
    period_start = payment_date
    period_end = calculate_membership_end_date(period_start, payment_data.membership_type)

    pay = Payment(
        owner_id=current.id,
        member_id=payment_data.member_id,
        amount=payment_data.amount,
        payment_date=payment_date,
        payment_method=payment_data.payment_method,
        status=PaymentStatus.PAID,
        membership_type=payment_data.membership_type,
        period_start=period_start,
        period_end=period_end,
        notes=payment_data.notes,
    )
    await db.payments.insert_one(pay.dict())
    await db.members.update_one(
        {"owner_id": current.id, "id": payment_data.member_id},
        {"$set": {"membership_end_date": period_end, "status": MemberStatus.ACTIVE}},
    )
    return pay

@api.get("/payments", response_model=List[Payment])
async def get_payments(skip: int = 0, limit: int = 100, member_id: Optional[str] = None, current: UserPublic = Depends(get_current_user)):
    q: Dict = {"owner_id": current.id}
    if member_id:
        q["member_id"] = member_id
    items = await db.payments.find(q).sort("payment_date", -1).skip(skip).limit(limit).to_list(limit)
    return [Payment(**i) for i in items]

@api.get("/payments/member/{member_id}", response_model=List[Payment])
async def get_member_payments(member_id: str, current: UserPublic = Depends(get_current_user)):
    items = await db.payments.find({"owner_id": current.id, "member_id": member_id}).sort("payment_date", -1).to_list(100)
    return [Payment(**i) for i in items]


# =========================
# Attendance — scoped
# =========================
@api.post("/attendance/checkin", response_model=Attendance)
async def check_in_member(attendance_data: AttendanceCreate, current: UserPublic = Depends(get_current_user)):
    member = await db.members.find_one({"owner_id": current.id, "id": attendance_data.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = await db.attendance.find_one({"owner_id": current.id, "member_id": attendance_data.member_id, "date": today, "check_out_time": None})
    if existing:
        raise HTTPException(status_code=400, detail="Member already checked in today")

    rec = Attendance(owner_id=current.id, member_id=attendance_data.member_id, check_in_time=datetime.utcnow(), date=today)
    await db.attendance.insert_one(rec.dict())
    return rec

@api.post("/attendance/checkout/{member_id}")
async def check_out_member(member_id: str, current: UserPublic = Depends(get_current_user)):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    rec = await db.attendance.find_one({"owner_id": current.id, "member_id": member_id, "date": today, "check_out_time": None})
    if not rec:
        raise HTTPException(status_code=404, detail="No active check-in found for today")
    await db.attendance.update_one({"owner_id": current.id, "id": rec["id"]}, {"$set": {"check_out_time": datetime.utcnow()}})
    return {"message": "Member checked out successfully"}

@api.get("/attendance", response_model=List[Attendance])
async def get_attendance(skip: int = 0, limit: int = 100, date: Optional[datetime] = None, current: UserPublic = Depends(get_current_user)):
    q: Dict = {"owner_id": current.id}
    if date:
        q["date"] = date.replace(hour=0, minute=0, second=0, microsecond=0)
    items = await db.attendance.find(q).sort("check_in_time", -1).skip(skip).limit(limit).to_list(limit)
    return [Attendance(**i) for i in items]


# =========================
# Dashboard — scoped
# =========================
@api.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current: UserPublic = Depends(get_current_user)):
    total_members = await db.members.count_documents({"owner_id": current.id})
    active_members = await db.members.count_documents({"owner_id": current.id, "status": MemberStatus.ACTIVE})

    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_payments = await db.payments.find({"owner_id": current.id, "payment_date": {"$gte": current_month_start}, "status": PaymentStatus.PAID}).to_list(1000)
    monthly_revenue = sum(p["amount"] for p in monthly_payments)

    now = datetime.utcnow()
    expired_members = await db.members.count_documents({"owner_id": current.id, "membership_end_date": {"$lt": now}, "status": MemberStatus.ACTIVE})

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_checkins = await db.attendance.count_documents({"owner_id": current.id, "date": today})

    return DashboardStats(
        total_members=total_members,
        active_members=active_members,
        monthly_revenue=monthly_revenue,
        pending_payments=expired_members,
        todays_checkins=todays_checkins,
    )


# =========================
# Register router & middleware
# =========================
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
