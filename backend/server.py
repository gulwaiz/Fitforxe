from fastapi import FastAPI, APIRouter, HTTPException, Request
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
from datetime import datetime, timedelta
from enum import Enum

import stripe, anyio
import razorpay

# ---------- Load env ----------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---------- Mongo ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ---------- Stripe ----------
stripe_api_key = os.environ.get("STRIPE_API_KEY")
if not stripe_api_key:
    logging.warning("STRIPE_API_KEY not found in environment variables")
stripe.api_key = stripe_api_key

# ---------- Razorpay ----------
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

# ---------- FastAPI ----------
app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---------- Enums ----------
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

# ---------- Models ----------
class GymOwnerProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    gateway: str  # "stripe" or "razorpay"
    payment_url: Optional[str] = None  # For Stripe (not used with official SDK here)
    order_id: Optional[str] = None     # For Razorpay
    amount: float
    currency: str
    razorpay_key_id: Optional[str] = None  # Public key for Razorpay frontend

class Attendance(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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

# ---------- Pricing ----------
MEMBERSHIP_PRICING = {
    MembershipType.BASIC: 29.99,
    MembershipType.PREMIUM: 49.99,
    MembershipType.VIP: 79.99,
}

# ---------- Helpers ----------
def calculate_membership_end_date(start_date: datetime, membership_type: MembershipType) -> datetime:
    return start_date + timedelta(days=30)

# ---------- Profile Routes ----------
@api_router.post("/profile", response_model=GymOwnerProfile)
async def create_or_update_profile(profile_data: GymOwnerProfileCreate):
    existing_profile = await db.gym_owner_profile.find_one({})
    if existing_profile:
        update_data = profile_data.dict()
        update_data["updated_at"] = datetime.utcnow()
        await db.gym_owner_profile.update_one({"id": existing_profile["id"]}, {"$set": update_data})
        updated_profile = await db.gym_owner_profile.find_one({"id": existing_profile["id"]})
        return GymOwnerProfile(**updated_profile)
    else:
        profile = GymOwnerProfile(**profile_data.dict())
        await db.gym_owner_profile.insert_one(profile.dict())
        return profile

@api_router.get("/profile", response_model=GymOwnerProfile)
async def get_profile():
    profile = await db.gym_owner_profile.find_one({})
    if not profile:
        return GymOwnerProfile(
            owner_name="Gym Owner",
            email="owner@fitforce.com",
            phone="+1-555-0000",
            address="123 Fitness Street",
            city="Gym City",
            state="GY",
            zip_code="12345",
        )
    return GymOwnerProfile(**profile)

@api_router.put("/profile", response_model=GymOwnerProfile)
async def update_profile(profile_update: GymOwnerProfileUpdate):
    existing_profile = await db.gym_owner_profile.find_one({})
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    await db.gym_owner_profile.update_one({"id": existing_profile["id"]}, {"$set": update_data})
    updated_profile = await db.gym_owner_profile.find_one({"id": existing_profile["id"]})
    return GymOwnerProfile(**updated_profile)

# ---------- Members ----------
@api_router.post("/members", response_model=Member)
async def create_member(member_data: MemberCreate):
    existing_member = await db.members.find_one({"email": member_data.email})
    if existing_member:
        raise HTTPException(status_code=400, detail="Member with this email already exists")

    start_date = datetime.utcnow()
    end_date = calculate_membership_end_date(start_date, member_data.membership_type)
    member_dict = member_data.dict()
    member_dict.update(
        {
            "membership_start_date": start_date,
            "membership_end_date": end_date,
            "status": MemberStatus.ACTIVE,
        }
    )
    enable_auto_billing = member_dict.pop("enable_auto_billing", False)
    member_dict["auto_billing_enabled"] = enable_auto_billing

    member = Member(**member_dict)
    await db.members.insert_one(member.dict())
    return member

@api_router.get("/members", response_model=List[Member])
async def get_members(skip: int = 0, limit: int = 100, status: Optional[MemberStatus] = None):
    query = {}
    if status:
        query["status"] = status
    members = await db.members.find(query).skip(skip).limit(limit).to_list(limit)
    return [Member(**m) for m in members]

@api_router.get("/members/{member_id}", response_model=Member)
async def get_member(member_id: str):
    member = await db.members.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return Member(**member)

@api_router.put("/members/{member_id}", response_model=Member)
async def update_member(member_id: str, member_update: MemberUpdate):
    member = await db.members.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    update_data = {k: v for k, v in member_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    await db.members.update_one({"id": member_id}, {"$set": update_data})
    updated_member = await db.members.find_one({"id": member_id})
    return Member(**updated_member)

@api_router.delete("/members/{member_id}")
async def delete_member(member_id: str):
    member = await db.members.find_one({"id": member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.members.delete_one({"id": member_id})
    return {"message": "Member deleted successfully"}

# ---------- Razorpay ----------
@api_router.post("/razorpay/create-order", response_model=PaymentGatewayResponse)
async def create_razorpay_order(request: RazorpayOrderRequest):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    member = await db.members.find_one({"id": request.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    amount_usd = MEMBERSHIP_PRICING[request.membership_type]
    amount_inr = amount_usd * 83  # approx
    amount_paise = int(amount_inr * 100)

    try:
        razorpay_order = razorpay_client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "member_id": request.member_id,
                    "membership_type": request.membership_type,
                    "gym_name": "FitForce",
                    "customer_name": request.customer_name,
                    "customer_email": request.customer_email,
                },
            }
        )

        payment_transaction = PaymentTransaction(
            member_id=request.member_id,
            session_id=razorpay_order["id"],
            amount=amount_inr,
            currency="INR",
            payment_method=PaymentMethodType.RAZORPAY,
            status=PaymentTransactionStatus.INITIATED,
            membership_type=request.membership_type,
            metadata={
                "gateway": "razorpay",
                "customer_name": request.customer_name,
                "customer_email": request.customer_email,
                "customer_phone": request.customer_phone,
                "customer_country": request.customer_country,
            },
        )
        await db.payment_transactions.insert_one(payment_transaction.dict())

        return PaymentGatewayResponse(
            gateway="razorpay",
            order_id=razorpay_order["id"],
            amount=amount_inr,
            currency="INR",
            razorpay_key_id=razorpay_key_id,
        )
    except Exception as e:
        logging.error(f"Razorpay order creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")

@api_router.post("/razorpay/verify-payment")
async def verify_razorpay_payment(request: Request):
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

        payment_transaction = await db.payment_transactions.find_one({"session_id": razorpay_order_id})
        if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one(
                {"session_id": razorpay_order_id},
                {"$set": {"status": PaymentTransactionStatus.COMPLETED, "payment_id": razorpay_payment_id, "updated_at": datetime.utcnow()}},
            )

            payment = Payment(
                member_id=payment_transaction["member_id"],
                amount=payment_transaction["amount"],
                payment_date=datetime.utcnow(),
                payment_method="razorpay",
                status=PaymentStatus.PAID,
                membership_type=payment_transaction["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                notes="Razorpay payment verified and processed",
            )
            await db.payments.insert_one(payment.dict())
            await db.members.update_one(
                {"id": payment_transaction["member_id"]},
                {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
            )

        return {"status": "success", "message": "Payment verified successfully"}
    except razorpay.errors.SignatureVerificationError:
        logging.error("Razorpay signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        logging.error(f"Razorpay payment verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Payment verification failed")

@api_router.post("/webhook/razorpay")
async def handle_razorpay_webhook(request: Request):
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "YOUR_WEBHOOK_SECRET")
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    try:
        webhook_body = await request.body()
        webhook_signature = request.headers.get("X-Razorpay-Signature", "")
        # Optionally verify webhook signature here with webhook_secret

        webhook_data = await request.json()
        event_type = webhook_data.get("event")

        if event_type == "payment.captured":
            payment_data = webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_data.get("order_id")
            payment_id = payment_data.get("id")

            payment_transaction = await db.payment_transactions.find_one({"session_id": order_id})
            if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
                await db.payment_transactions.update_one(
                    {"session_id": order_id},
                    {"$set": {"status": PaymentTransactionStatus.COMPLETED, "payment_id": payment_id, "updated_at": datetime.utcnow()}},
                )

                payment = Payment(
                    member_id=payment_transaction["member_id"],
                    amount=payment_transaction["amount"],
                    payment_date=datetime.utcnow(),
                    payment_method="razorpay",
                    status=PaymentStatus.PAID,
                    membership_type=payment_transaction["membership_type"],
                    period_start=datetime.utcnow(),
                    period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                    notes="Razorpay webhook processed",
                )
                await db.payments.insert_one(payment.dict())
                await db.members.update_one(
                    {"id": payment_transaction["member_id"]},
                    {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
                )

        return {"status": "success"}
    except Exception as e:
        logging.error(f"Razorpay webhook processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

# ---------- Utility ----------
@api_router.get("/detect-country")
async def detect_country(request: Request):
    try:
        client_ip = request.client.host
        if client_ip.startswith(("127.0.0.", "::1", "192.168.")):
            return {"country": "IN", "country_name": "India"}
        return {"country": "US", "country_name": "United States"}
    except Exception as e:
        logging.error(f"Country detection failed: {str(e)}")
        return {"country": "US", "country_name": "United States"}

# ---------- STRIPE (Official SDK) ----------
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

@api_router.post("/stripe/checkout", response_model=CheckoutSessionResponse)
async def create_stripe_checkout(request: CheckoutSessionRequest):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    member = await db.members.find_one({"id": request.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    amount = MEMBERSHIP_PRICING[request.membership_type]

    def _create():
        return stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"{request.membership_type.capitalize()} Membership"},
                        "unit_amount": int(amount * 100),
                    },
                    "quantity": 1,
                }
            ],
            success_url=request.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.cancel_url,
            metadata={
                "member_id": request.member_id,
                "membership_type": request.membership_type,
                "gym_name": "FitForce",
            },
        )

    session = await anyio.to_thread.run_sync(_create)

    payment_transaction = PaymentTransaction(
        member_id=request.member_id,
        session_id=session.id,
        amount=amount,
        currency="usd",
        payment_method=PaymentMethodType.STRIPE,
        status=PaymentTransactionStatus.INITIATED,
        membership_type=request.membership_type,
        metadata={"gateway": "stripe"},
    )
    await db.payment_transactions.insert_one(payment_transaction.dict())

    return CheckoutSessionResponse(session_id=session.id, url=session.url)

@api_router.get("/stripe/checkout/status/{session_id}", response_model=CheckoutStatusResponse)
async def get_stripe_checkout_status(session_id: str):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    def _retrieve():
        return stripe.checkout.Session.retrieve(session_id)

    sess = await anyio.to_thread.run_sync(_retrieve)
    payment_status = sess.get("payment_status") or sess.get("status") or "unknown"

    if payment_status == "paid":
        payment_transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"status": PaymentTransactionStatus.COMPLETED, "updated_at": datetime.utcnow()}},
            )
            payment = Payment(
                member_id=payment_transaction["member_id"],
                amount=payment_transaction["amount"],
                payment_date=datetime.utcnow(),
                payment_method="stripe",
                status=PaymentStatus.PAID,
                membership_type=payment_transaction["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                notes="Stripe payment processed",
            )
            await db.payments.insert_one(payment.dict())
            await db.members.update_one(
                {"id": payment_transaction["member_id"]},
                {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
            )

    return CheckoutStatusResponse(payment_status=payment_status)

@api_router.post("/webhook/stripe")
async def handle_stripe_webhook(request: Request):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")

    payload = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")  # optional

    try:
        def _construct():
            if endpoint_secret:
                return stripe.Webhook.construct_event(payload, sig, endpoint_secret)
            else:
                # If you don't set a webhook secret, skip verification (not recommended for production)
                return stripe.Event.construct_from({"type": "unchecked", "data": {"object": {}}}, stripe.api_key)

        event = await anyio.to_thread.run_sync(_construct)
    except Exception as e:
        logging.error(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload/signature")

    if event and event.get("type") == "checkout.session.completed":
        session_id = event["data"]["object"]["id"]
        payment_transaction = await db.payment_transactions.find_one({"session_id": session_id})
        if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {"status": PaymentTransactionStatus.COMPLETED, "updated_at": datetime.utcnow()}},
            )
            payment = Payment(
                member_id=payment_transaction["member_id"],
                amount=payment_transaction["amount"],
                payment_date=datetime.utcnow(),
                payment_method="stripe",
                status=PaymentStatus.PAID,
                membership_type=payment_transaction["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                notes="Stripe webhook processed",
            )
            await db.payments.insert_one(payment.dict())
            await db.members.update_one(
                {"id": payment_transaction["member_id"]},
                {"$set": {"membership_end_date": payment.period_end, "status": MemberStatus.ACTIVE, "auto_billing_enabled": True}},
            )

    return {"status": "success"}

# ---------- Payments ----------
@api_router.post("/payments", response_model=Payment)
async def create_payment(payment_data: PaymentCreate):
    member = await db.members.find_one({"id": payment_data.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    payment_date = datetime.utcnow()
    period_start = payment_date
    period_end = calculate_membership_end_date(period_start, payment_data.membership_type)

    payment_dict = payment_data.dict()
    payment_dict.update(
        {
            "payment_date": payment_date,
            "status": PaymentStatus.PAID,
            "period_start": period_start,
            "period_end": period_end,
        }
    )

    payment = Payment(**payment_dict)
    await db.payments.insert_one(payment.dict())
    await db.members.update_one({"id": payment_data.member_id}, {"$set": {"membership_end_date": period_end, "status": MemberStatus.ACTIVE}})
    return payment

@api_router.get("/payments", response_model=List[Payment])
async def get_payments(skip: int = 0, limit: int = 100, member_id: Optional[str] = None):
    query = {}
    if member_id:
        query["member_id"] = member_id
    payments = await db.payments.find(query).sort("payment_date", -1).skip(skip).limit(limit).to_list(limit)
    return [Payment(**p) for p in payments]

@api_router.get("/payments/member/{member_id}", response_model=List[Payment])
async def get_member_payments(member_id: str):
    payments = await db.payments.find({"member_id": member_id}).sort("payment_date", -1).to_list(100)
    return [Payment(**p) for p in payments]

# ---------- Attendance ----------
@api_router.post("/attendance/checkin", response_model=Attendance)
async def check_in_member(attendance_data: AttendanceCreate):
    member = await db.members.find_one({"id": attendance_data.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing_attendance = await db.attendance.find_one(
        {"member_id": attendance_data.member_id, "date": today, "check_out_time": None}
    )
    if existing_attendance:
        raise HTTPException(status_code=400, detail="Member already checked in today")

    attendance = Attendance(member_id=attendance_data.member_id, check_in_time=datetime.utcnow(), date=today)
    await db.attendance.insert_one(attendance.dict())
    return attendance

@api_router.post("/attendance/checkout/{member_id}")
async def check_out_member(member_id: str):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    attendance = await db.attendance.find_one({"member_id": member_id, "date": today, "check_out_time": None})
    if not attendance:
        raise HTTPException(status_code=404, detail="No active check-in found for today")

    await db.attendance.update_one({"id": attendance["id"]}, {"$set": {"check_out_time": datetime.utcnow()}})
    return {"message": "Member checked out successfully"}

@api_router.get("/attendance", response_model=List[Attendance])
async def get_attendance(skip: int = 0, limit: int = 100, date: Optional[datetime] = None):
    query = {}
    if date:
        query["date"] = date.replace(hour=0, minute=0, second=0, microsecond=0)
    records = await db.attendance.find(query).sort("check_in_time", -1).skip(skip).limit(limit).to_list(limit)
    return [Attendance(**r) for r in records]

# ---------- Dashboard ----------
@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    total_members = await db.members.count_documents({})
    active_members = await db.members.count_documents({"status": MemberStatus.ACTIVE})

    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_payments = await db.payments.find(
        {"payment_date": {"$gte": current_month_start}, "status": PaymentStatus.PAID}
    ).to_list(1000)
    monthly_revenue = sum(p["amount"] for p in monthly_payments)

    now = datetime.utcnow()
    expired_members = await db.members.count_documents({"membership_end_date": {"$lt": now}, "status": MemberStatus.ACTIVE})

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_checkins = await db.attendance.count_documents({"date": today})

    return DashboardStats(
        total_members=total_members,
        active_members=active_members,
        monthly_revenue=monthly_revenue,
        pending_payments=expired_members,
        todays_checkins=todays_checkins,
    )

@api_router.get("/membership-pricing")
async def get_membership_pricing():
    return MEMBERSHIP_PRICING

# ---------- Register router & middleware ----------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Shutdown ----------
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
