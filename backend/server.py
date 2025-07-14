from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

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

# Models
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

# Member Routes
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

# Payment Routes
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