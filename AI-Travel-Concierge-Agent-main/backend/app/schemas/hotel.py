from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class HotelOut(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)
