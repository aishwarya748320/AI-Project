import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, JSON
from app.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    booking_reference = Column(String(50), unique=True, index=True, nullable=False)
    offer_id = Column(String(100), index=True, nullable=False)
    
    customer_name = Column(String(150), nullable=False)
    customer_email = Column(String(150), nullable=False)
    customer_phone = Column(String(50), nullable=True)
    passenger_count = Column(Integer, nullable=False, default=1)
    
    total_charged = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="INR")
    data_source = Column(String(30), nullable=False, default="SIMULATED")
    status = Column(String(50), nullable=False, default="CONFIRMED_SIMULATED")
    
    package_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<Booking {self.booking_reference} offer={self.offer_id} status={self.status}>"
