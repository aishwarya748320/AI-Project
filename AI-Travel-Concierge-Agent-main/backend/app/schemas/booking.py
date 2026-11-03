from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class VerifyOfferRequest(BaseModel):
    offer_id: str = Field(..., description="Unique offer identifier to revalidate")
    expected_price: float = Field(..., gt=0, description="Expected price quoted to traveler")
    currency: str = Field("INR", description="Currency of quoted fare")
    package_details: Optional[Dict[str, Any]] = Field(default=None, description="Optional package context for revalidation")

class VerifyOfferResponse(BaseModel):
    verified: bool
    status: str
    offer_id: str
    data_source: str
    currency: str = "INR"
    current_price: Optional[float] = None
    price_difference: Optional[float] = None
    message: str

class BookingCustomerDetails(BaseModel):
    name: str = Field(..., min_length=2, description="Primary traveler full name")
    email: str = Field(..., description="Contact email for confirmation")
    phone: Optional[str] = Field(None, description="Contact phone number")
    passenger_count: int = Field(1, ge=1, description="Number of traveling passengers")

class BookingConfirmRequest(BaseModel):
    offer_id: str = Field(..., description="Offer identifier to book")
    confirm: bool = Field(..., description="Explicit user confirmation flag. Must be True.")
    customer: BookingCustomerDetails = Field(..., description="Traveler contact details")
    package_details: Dict[str, Any] = Field(default_factory=dict, description="Package snapshot")

class BookingConfirmResponse(BaseModel):
    success: bool
    status: str
    booking_reference: Optional[str] = None
    data_source: str
    currency: str = "INR"
    total_charged: float = 0.0
    customer_name: Optional[str] = None
    handoff_url: Optional[str] = None
    disclaimer: str
    message: str
