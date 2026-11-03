from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.agent.types import TravelPackage, RejectionSummary

class RecommendationRequest(BaseModel):
    departure_city: str = Field(..., json_schema_extra={"example": "Delhi"}, description="Origin city")
    destination_city: str = Field(..., json_schema_extra={"example": "Mumbai"}, description="Destination city")
    departure_date: date = Field(..., json_schema_extra={"example": "2026-11-10"}, description="Departure date (YYYY-MM-DD)")
    return_date: date = Field(..., json_schema_extra={"example": "2026-11-14"}, description="Return date (YYYY-MM-DD)")
    adults: int = Field(1, ge=1, json_schema_extra={"example": 2}, description="Number of adult travelers")
    budget: float = Field(..., gt=0, json_schema_extra={"example": 50000.0}, description="Total budget in INR")
    
    preferred_hotel_stars: Optional[int] = Field(None, ge=1, le=5, json_schema_extra={"example": 4}, description="Preferred star rating (3, 4, 5)")
    hotel_category_is_hard: bool = Field(True, description="Enforce hotel category strictly")
    
    preferred_airline: Optional[str] = Field(None, json_schema_extra={"example": "IndiGo"}, description="Preferred airline carrier")
    max_flight_stops: Optional[int] = Field(None, ge=0, json_schema_extra={"example": 0}, description="Max acceptable flight stops")
    max_flight_stops_is_hard: bool = Field(False, description="Treat max stops as hard constraint")
    max_layover_minutes: Optional[int] = Field(None, ge=0, json_schema_extra={"example": 120}, description="Max layover minutes")
    
    preferred_amenities: List[str] = Field(default_factory=list, json_schema_extra={"example": ["Swimming Pool", "Breakfast Included"]})
    amenities_are_hard: bool = Field(False, description="Treat amenities as mandatory hard constraint")
    
    room_sharing: bool = Field(True, description="Share rooms up to max occupancy")
    rooms_per_party: Optional[int] = Field(None, ge=1, description="Explicit room count requested")


class RecommendationResponse(BaseModel):
    id: Optional[str] = None
    status: str
    message: str
    data_source: str = "SIMULATED"
    currency: str = "INR"
    best_package: Optional[TravelPackage] = None
    alternative_packages: List[TravelPackage] = Field(default_factory=list)
    explanation: str
    itemized_cost_breakdown: Optional[dict] = None
    assumptions: List[str] = Field(default_factory=list)
    actionable_suggestions: List[str] = Field(default_factory=list)
    rejection_summary: RejectionSummary = Field(default_factory=RejectionSummary)
    booking_status: Optional[str] = None
    booking_handoff_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RecommendationHistoryItem(BaseModel):
    id: str
    created_at: datetime
    departure_city: str
    destination_city: str
    departure_date: date
    return_date: date
    adults: int
    budget: float
    status: str

    model_config = ConfigDict(from_attributes=True)
