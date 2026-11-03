from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class FlightOut(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)
