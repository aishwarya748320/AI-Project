from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class TravelRequirements(BaseModel):
    """User input travel requirements parsed and validated in Stage 1."""
    departure_city: str
    destination_city: str
    departure_date: date
    return_date: date
    adults: int = Field(gt=0, description="Must have at least 1 adult traveler")
    budget: float = Field(gt=0, description="Total budget in INR must be positive")
    preferred_hotel_stars: Optional[int] = Field(default=None, ge=1, le=5)
    hotel_category_is_hard: bool = True
    
    preferred_airline: Optional[str] = None
    max_flight_stops: Optional[int] = None
    max_flight_stops_is_hard: bool = False
    max_layover_minutes: Optional[int] = None
    
    preferred_amenities: List[str] = Field(default_factory=list)
    amenities_are_hard: bool = False
    
    room_sharing: bool = True
    rooms_per_party: Optional[int] = None  # None = auto-calculate based on occupancy

    @property
    def nights(self) -> int:
        delta = (self.return_date - self.departure_date).days
        return max(1, delta)


class FlightDTO(BaseModel):
    id: int
    flight_number: str
    airline: str
    origin_city: str
    origin_code: str
    destination_city: str
    destination_code: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    layover_duration_minutes: int
    price_per_adult: float
    available_seats: int
    data_source: str = "SIMULATED"
    currency: str = "INR"
    offer_id: Optional[str] = None


class HotelDTO(BaseModel):
    id: int
    name: str
    city: str
    star_rating: int
    price_per_night: float
    amenities: List[str]
    available_rooms: int
    max_occupancy_per_room: int
    description: Optional[str] = None
    image_url: Optional[str] = None
    data_source: str = "SIMULATED"
    currency: str = "INR"
    offer_id: Optional[str] = None


class TravelPackage(BaseModel):
    """A feasible candidate package combining outbound flight, return flight, and hotel."""
    package_id: Optional[str] = None
    data_source: str = "SIMULATED"
    currency: str = "INR"

    outbound_flight: FlightDTO
    return_flight: FlightDTO
    hotel: HotelDTO
    
    nights: int
    rooms_required: int
    
    flight_cost: float
    hotel_cost: float
    total_cost: float
    remaining_budget: float

    itemized_cost_breakdown: Optional[Dict[str, Any]] = None
    assumptions: List[str] = Field(default_factory=list)

    # Soft constraint score / penalty metric
    convenience_score: float = 0.0
    soft_penalties: List[str] = Field(default_factory=list)
    is_relaxed_hotel_category: bool = False


class ConstraintViolation(BaseModel):
    constraint_name: str
    reason: str
    is_hard: bool = True


class RejectionSummary(BaseModel):
    total_combinations_evaluated: int = 0
    route_incompatible: int = 0
    date_incompatible: int = 0
    insufficient_flight_seats: int = 0
    insufficient_hotel_rooms: int = 0
    hotel_stars_mismatch: int = 0
    stops_exceeded: int = 0
    budget_exceeded: int = 0
    layover_exceeded: int = 0
    amenities_missing: int = 0


class AgentResult(BaseModel):
    status: str  # "SUCCESS", "NO_FEASIBLE_PACKAGE", "INVALID_INPUT"
    message: str
    data_source: str = "SIMULATED"
    currency: str = "INR"
    best_package: Optional[TravelPackage] = None
    alternative_packages: List[TravelPackage] = Field(default_factory=list)
    explanation: str
    itemized_cost_breakdown: Optional[Dict[str, Any]] = None
    assumptions: List[str] = Field(default_factory=list)
    actionable_suggestions: List[str] = Field(default_factory=list)
    rejection_summary: RejectionSummary = Field(default_factory=RejectionSummary)
