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
from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Stripe configuration
stripe_api_key = os.environ.get('STRIPE_API_KEY')
if not stripe_api_key:
    logging.warning("STRIPE_API_KEY not found in environment variables")

# Razorpay configuration
# TODO: Replace with your actual Razorpay API keys from https://dashboard.razorpay.com/
razorpay_key_id = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_YOUR_KEY_ID')  # Insert your Razorpay Key ID here
razorpay_key_secret = os.environ.get('RAZORPAY_KEY_SECRET', 'YOUR_KEY_SECRET')  # Insert your Razorpay Key Secret here

import razorpay
razorpay_client = None
if razorpay_key_id and razorpay_key_secret:
    try:
        razorpay_client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
    except Exception as e:
        logging.warning(f"Razorpay client initialization failed: {e}")
else:
    logging.warning("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not found in environment variables")

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
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
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"

# Models
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

class StripeCheckoutRequest(BaseModel):
    member_id: str
    membership_type: MembershipType
    success_url: str
    cancel_url: str

class RazorpayOrderRequest(BaseModel):
    member_id: str
    membership_type: MembershipType
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_country: str

class PaymentGatewayResponse(BaseModel):
    gateway: str  # "stripe" or "razorpay"
    payment_url: Optional[str] = None  # For Stripe
    order_id: Optional[str] = None  # For Razorpay
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

# Membership pricing
MEMBERSHIP_PRICING = {
    MembershipType.BASIC: 29.99,
    MembershipType.PREMIUM: 49.99,
    MembershipType.VIP: 79.99
}

# Helper functions
def calculate_membership_end_date(start_date: datetime, membership_type: MembershipType) -> datetime:
    # All memberships are monthly
    return start_date + timedelta(days=30)

# Gym Owner Profile Routes
@api_router.post("/profile", response_model=GymOwnerProfile)
async def create_or_update_profile(profile_data: GymOwnerProfileCreate):
    # Check if profile already exists
    existing_profile = await db.gym_owner_profile.find_one({})
    
    if existing_profile:
        # Update existing profile
        update_data = profile_data.dict()
        update_data["updated_at"] = datetime.utcnow()
        
        await db.gym_owner_profile.update_one(
            {"id": existing_profile["id"]},
            {"$set": update_data}
        )
        
        updated_profile = await db.gym_owner_profile.find_one({"id": existing_profile["id"]})
        return GymOwnerProfile(**updated_profile)
    else:
        # Create new profile
        profile = GymOwnerProfile(**profile_data.dict())
        await db.gym_owner_profile.insert_one(profile.dict())
        return profile

@api_router.get("/profile", response_model=GymOwnerProfile)
async def get_profile():
    profile = await db.gym_owner_profile.find_one({})
    if not profile:
        # Return default profile if none exists
        return GymOwnerProfile(
            owner_name="Gym Owner",
            email="owner@fitforce.com",
            phone="+1-555-0000",
            address="123 Fitness Street",
            city="Gym City",
            state="GY",
            zip_code="12345"
        )
    return GymOwnerProfile(**profile)

@api_router.put("/profile", response_model=GymOwnerProfile)
async def update_profile(profile_update: GymOwnerProfileUpdate):
    existing_profile = await db.gym_owner_profile.find_one({})
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    update_data = {k: v for k, v in profile_update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await db.gym_owner_profile.update_one(
        {"id": existing_profile["id"]},
        {"$set": update_data}
    )
    
    updated_profile = await db.gym_owner_profile.find_one({"id": existing_profile["id"]})
    return GymOwnerProfile(**updated_profile)
@api_router.post("/members", response_model=Member)
async def create_member(member_data: MemberCreate):
    # Check if email already exists
    existing_member = await db.members.find_one({"email": member_data.email})
    if existing_member:
        raise HTTPException(status_code=400, detail="Member with this email already exists")
    
    # Calculate membership dates
    start_date = datetime.utcnow()
    end_date = calculate_membership_end_date(start_date, member_data.membership_type)
    
    member_dict = member_data.dict()
    member_dict.update({
        "membership_start_date": start_date,
        "membership_end_date": end_date,
        "status": MemberStatus.ACTIVE
    })
    
    # Remove enable_auto_billing from member_dict and set auto_billing_enabled
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
    return [Member(**member) for member in members]

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

# Razorpay Payment Routes
@api_router.post("/razorpay/create-order", response_model=PaymentGatewayResponse)
async def create_razorpay_order(request: RazorpayOrderRequest):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    
    # Verify member exists
    member = await db.members.find_one({"id": request.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Get pricing (convert to paise - Razorpay uses smallest currency unit)
    amount_usd = MEMBERSHIP_PRICING[request.membership_type]
    amount_inr = amount_usd * 83  # Approximate USD to INR conversion
    amount_paise = int(amount_inr * 100)  # Convert to paise
    
    try:
        # Create Razorpay order
        razorpay_order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "payment_capture": 1,
            "notes": {
                "member_id": request.member_id,
                "membership_type": request.membership_type,
                "gym_name": "FitForce",
                "customer_name": request.customer_name,
                "customer_email": request.customer_email
            }
        })
        
        # Create payment transaction record
        payment_transaction = PaymentTransaction(
            member_id=request.member_id,
            session_id=razorpay_order["id"],
            amount=amount_inr,  # Store in INR
            currency="INR",
            payment_method=PaymentMethodType.STRIPE,  # We'll add RAZORPAY to enum
            status=PaymentTransactionStatus.INITIATED,
            membership_type=request.membership_type,
            metadata={
                "gateway": "razorpay",
                "customer_name": request.customer_name,
                "customer_email": request.customer_email,
                "customer_phone": request.customer_phone,
                "customer_country": request.customer_country
            }
        )
        
        await db.payment_transactions.insert_one(payment_transaction.dict())
        
        return PaymentGatewayResponse(
            gateway="razorpay",
            order_id=razorpay_order["id"],
            amount=amount_inr,
            currency="INR",
            razorpay_key_id=razorpay_key_id  # Public key safe to send to frontend
        )
        
    except Exception as e:
        logging.error(f"Razorpay order creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create Razorpay order: {str(e)}")

@api_router.post("/razorpay/verify-payment")
async def verify_razorpay_payment(request: Request):
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    
    try:
        # Get payment verification data from request
        body = await request.json()
        
        razorpay_order_id = body.get('razorpay_order_id')
        razorpay_payment_id = body.get('razorpay_payment_id')
        razorpay_signature = body.get('razorpay_signature')
        
        # Verify payment signature
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        }
        
        # Razorpay signature verification
        razorpay_client.utility.verify_payment_signature(params_dict)
        
        # Update payment transaction
        payment_transaction = await db.payment_transactions.find_one({"session_id": razorpay_order_id})
        if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
            # Update transaction status
            await db.payment_transactions.update_one(
                {"session_id": razorpay_order_id},
                {"$set": {
                    "status": PaymentTransactionStatus.COMPLETED,
                    "payment_id": razorpay_payment_id,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Create payment record
            payment = Payment(
                member_id=payment_transaction["member_id"],
                amount=payment_transaction["amount"],
                payment_date=datetime.utcnow(),
                payment_method="razorpay",
                status=PaymentStatus.PAID,
                membership_type=payment_transaction["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                notes="Razorpay payment verified and processed"
            )
            
            await db.payments.insert_one(payment.dict())
            
            # Update member's membership end date
            await db.members.update_one(
                {"id": payment_transaction["member_id"]},
                {"$set": {
                    "membership_end_date": payment.period_end,
                    "status": MemberStatus.ACTIVE,
                    "auto_billing_enabled": True
                }}
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
    # TODO: Add your Razorpay webhook secret here
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', 'YOUR_WEBHOOK_SECRET')
    
    if not razorpay_client:
        raise HTTPException(status_code=500, detail="Razorpay is not configured")
    
    try:
        # Get webhook payload and signature
        webhook_body = await request.body()
        webhook_signature = request.headers.get("X-Razorpay-Signature", "")
        
        # Verify webhook signature (uncomment when you have webhook secret)
        # razorpay_client.utility.verify_webhook_signature(
        #     webhook_body.decode(),
        #     webhook_signature,
        #     webhook_secret
        # )
        
        # Parse webhook payload
        webhook_data = await request.json()
        event_type = webhook_data.get("event")
        
        if event_type == "payment.captured":
            payment_data = webhook_data.get("payload", {}).get("payment", {}).get("entity", {})
            order_id = payment_data.get("order_id")
            payment_id = payment_data.get("id")
            
            # Update payment transaction
            payment_transaction = await db.payment_transactions.find_one({"session_id": order_id})
            if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
                await db.payment_transactions.update_one(
                    {"session_id": order_id},
                    {"$set": {
                        "status": PaymentTransactionStatus.COMPLETED,
                        "payment_id": payment_id,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                # Create payment record and update member (similar to verification endpoint)
                payment = Payment(
                    member_id=payment_transaction["member_id"],
                    amount=payment_transaction["amount"],
                    payment_date=datetime.utcnow(),
                    payment_method="razorpay",
                    status=PaymentStatus.PAID,
                    membership_type=payment_transaction["membership_type"],
                    period_start=datetime.utcnow(),
                    period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                    notes="Razorpay webhook processed"
                )
                
                await db.payments.insert_one(payment.dict())
                
                await db.members.update_one(
                    {"id": payment_transaction["member_id"]},
                    {"$set": {
                        "membership_end_date": payment.period_end,
                        "status": MemberStatus.ACTIVE,
                        "auto_billing_enabled": True
                    }}
                )
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Razorpay webhook processing failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")

# Country Detection Route
@api_router.get("/detect-country")
async def detect_country(request: Request):
    """Detect user's country based on IP address"""
    try:
        # Get client IP
        client_ip = request.client.host
        
        # For development, return a default country
        # TODO: In production, use a proper IP geolocation service like:
        # - MaxMind GeoLite2
        # - ipapi.com
        # - ip-api.com
        
        # For testing purposes, return India if IP starts with certain ranges
        # In production, replace this with actual geolocation logic
        if client_ip.startswith(('127.0.0.', '::1', '192.168.')):
            # Local development - return default based on environment
            return {"country": "IN", "country_name": "India"}
        
        # Simple mock geolocation - replace with real service
        return {"country": "US", "country_name": "United States"}
        
    except Exception as e:
        logging.error(f"Country detection failed: {str(e)}")
        return {"country": "US", "country_name": "United States"}  # Default fallback
# Stripe Payment Routes
@api_router.post("/stripe/checkout", response_model=CheckoutSessionResponse)
async def create_stripe_checkout(request: StripeCheckoutRequest):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    
    # Verify member exists
    member = await db.members.find_one({"id": request.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Initialize Stripe checkout
    host_url = request.success_url.split('/')[0] + '//' + request.success_url.split('/')[2]
    webhook_url = f"{host_url}/api/webhook/stripe"
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url=webhook_url)
    
    # Get pricing
    amount = MEMBERSHIP_PRICING[request.membership_type]
    
    # Create checkout session
    checkout_request = CheckoutSessionRequest(
        amount=amount,
        currency="usd",
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        metadata={
            "member_id": request.member_id,
            "membership_type": request.membership_type,
            "gym_name": "FitForce"
        }
    )
    
    session = await stripe_checkout.create_checkout_session(checkout_request)
    
    # Create payment transaction record
    payment_transaction = PaymentTransaction(
        member_id=request.member_id,
        session_id=session.session_id,
        amount=amount,
        currency="usd",
        payment_method=PaymentMethodType.STRIPE,
        status=PaymentTransactionStatus.INITIATED,
        membership_type=request.membership_type,
        metadata=checkout_request.metadata
    )
    
    await db.payment_transactions.insert_one(payment_transaction.dict())
    
    return session

@api_router.get("/stripe/checkout/status/{session_id}")
async def get_stripe_checkout_status(session_id: str):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    
    # Initialize Stripe checkout
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    # Get checkout status
    status = await stripe_checkout.get_checkout_status(session_id)
    
    # Update payment transaction
    payment_transaction = await db.payment_transactions.find_one({"session_id": session_id})
    if payment_transaction:
        if status.payment_status == "paid" and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
            # Update transaction status
            await db.payment_transactions.update_one(
                {"session_id": session_id},
                {"$set": {
                    "status": PaymentTransactionStatus.COMPLETED,
                    "updated_at": datetime.utcnow()
                }}
            )
            
            # Create payment record
            payment = Payment(
                member_id=payment_transaction["member_id"],
                amount=payment_transaction["amount"],
                payment_date=datetime.utcnow(),
                payment_method="stripe",
                status=PaymentStatus.PAID,
                membership_type=payment_transaction["membership_type"],
                period_start=datetime.utcnow(),
                period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                notes="Stripe payment processed"
            )
            
            await db.payments.insert_one(payment.dict())
            
            # Update member's membership end date
            await db.members.update_one(
                {"id": payment_transaction["member_id"]},
                {"$set": {
                    "membership_end_date": payment.period_end,
                    "status": MemberStatus.ACTIVE,
                    "auto_billing_enabled": True
                }}
            )
    
    return status

@api_router.post("/webhook/stripe")
async def handle_stripe_webhook(request: Request):
    if not stripe_api_key:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    
    # Initialize Stripe checkout
    stripe_checkout = StripeCheckout(api_key=stripe_api_key, webhook_url="")
    
    # Get webhook data
    webhook_body = await request.body()
    stripe_signature = request.headers.get("Stripe-Signature")
    
    try:
        webhook_response = await stripe_checkout.handle_webhook(webhook_body, stripe_signature)
        
        if webhook_response.event_type == "checkout.session.completed":
            session_id = webhook_response.session_id
            
            # Update payment transaction
            payment_transaction = await db.payment_transactions.find_one({"session_id": session_id})
            if payment_transaction and payment_transaction["status"] != PaymentTransactionStatus.COMPLETED:
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {
                        "status": PaymentTransactionStatus.COMPLETED,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                # Create payment record and update member (same logic as above)
                payment = Payment(
                    member_id=payment_transaction["member_id"],
                    amount=payment_transaction["amount"],
                    payment_date=datetime.utcnow(),
                    payment_method="stripe",
                    status=PaymentStatus.PAID,
                    membership_type=payment_transaction["membership_type"],
                    period_start=datetime.utcnow(),
                    period_end=calculate_membership_end_date(datetime.utcnow(), payment_transaction["membership_type"]),
                    notes="Stripe webhook processed"
                )
                
                await db.payments.insert_one(payment.dict())
                
                await db.members.update_one(
                    {"id": payment_transaction["member_id"]},
                    {"$set": {
                        "membership_end_date": payment.period_end,
                        "status": MemberStatus.ACTIVE,
                        "auto_billing_enabled": True
                    }}
                )
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")
@api_router.post("/payments", response_model=Payment)
async def create_payment(payment_data: PaymentCreate):
    # Verify member exists
    member = await db.members.find_one({"id": payment_data.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Calculate payment period
    payment_date = datetime.utcnow()
    period_start = payment_date
    period_end = calculate_membership_end_date(period_start, payment_data.membership_type)
    
    payment_dict = payment_data.dict()
    payment_dict.update({
        "payment_date": payment_date,
        "status": PaymentStatus.PAID,
        "period_start": period_start,
        "period_end": period_end
    })
    
    payment = Payment(**payment_dict)
    await db.payments.insert_one(payment.dict())
    
    # Update member's membership end date
    await db.members.update_one(
        {"id": payment_data.member_id},
        {"$set": {"membership_end_date": period_end, "status": MemberStatus.ACTIVE}}
    )
    
    return payment

@api_router.get("/payments", response_model=List[Payment])
async def get_payments(skip: int = 0, limit: int = 100, member_id: Optional[str] = None):
    query = {}
    if member_id:
        query["member_id"] = member_id
    
    payments = await db.payments.find(query).sort("payment_date", -1).skip(skip).limit(limit).to_list(limit)
    return [Payment(**payment) for payment in payments]

@api_router.get("/payments/member/{member_id}", response_model=List[Payment])
async def get_member_payments(member_id: str):
    payments = await db.payments.find({"member_id": member_id}).sort("payment_date", -1).to_list(100)
    return [Payment(**payment) for payment in payments]

# Attendance Routes
@api_router.post("/attendance/checkin", response_model=Attendance)
async def check_in_member(attendance_data: AttendanceCreate):
    # Verify member exists
    member = await db.members.find_one({"id": attendance_data.member_id})
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Check if already checked in today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing_attendance = await db.attendance.find_one({
        "member_id": attendance_data.member_id,
        "date": today,
        "check_out_time": None
    })
    
    if existing_attendance:
        raise HTTPException(status_code=400, detail="Member already checked in today")
    
    attendance = Attendance(
        member_id=attendance_data.member_id,
        check_in_time=datetime.utcnow(),
        date=today
    )
    
    await db.attendance.insert_one(attendance.dict())
    return attendance

@api_router.post("/attendance/checkout/{member_id}")
async def check_out_member(member_id: str):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    attendance = await db.attendance.find_one({
        "member_id": member_id,
        "date": today,
        "check_out_time": None
    })
    
    if not attendance:
        raise HTTPException(status_code=404, detail="No active check-in found for today")
    
    await db.attendance.update_one(
        {"id": attendance["id"]},
        {"$set": {"check_out_time": datetime.utcnow()}}
    )
    
    return {"message": "Member checked out successfully"}

@api_router.get("/attendance", response_model=List[Attendance])
async def get_attendance(skip: int = 0, limit: int = 100, date: Optional[datetime] = None):
    query = {}
    if date:
        query["date"] = date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    attendance_records = await db.attendance.find(query).sort("check_in_time", -1).skip(skip).limit(limit).to_list(limit)
    return [Attendance(**record) for record in attendance_records]

# Dashboard Routes
@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    # Total members
    total_members = await db.members.count_documents({})
    
    # Active members
    active_members = await db.members.count_documents({"status": MemberStatus.ACTIVE})
    
    # Monthly revenue (current month)
    current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_payments = await db.payments.find({
        "payment_date": {"$gte": current_month_start},
        "status": PaymentStatus.PAID
    }).to_list(1000)
    monthly_revenue = sum(payment["amount"] for payment in monthly_payments)
    
    # Pending payments (members with expired memberships)
    now = datetime.utcnow()
    expired_members = await db.members.count_documents({
        "membership_end_date": {"$lt": now},
        "status": MemberStatus.ACTIVE
    })
    
    # Today's check-ins
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    todays_checkins = await db.attendance.count_documents({"date": today})
    
    return DashboardStats(
        total_members=total_members,
        active_members=active_members,
        monthly_revenue=monthly_revenue,
        pending_payments=expired_members,
        todays_checkins=todays_checkins
    )

@api_router.get("/membership-pricing")
async def get_membership_pricing():
    return MEMBERSHIP_PRICING

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()