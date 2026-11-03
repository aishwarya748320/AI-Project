from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.hotel import Hotel
from app.schemas.hotel import HotelOut

router = APIRouter(prefix="/hotels", tags=["Hotels"])

@router.get("", response_model=List[HotelOut])
def get_hotels(
    city: Optional[str] = Query(None, description="Hotel city e.g. Mumbai"),
    star_rating: Optional[int] = Query(None, ge=1, le=5, description="Star rating (3, 4, 5)"),
    max_price: Optional[float] = Query(None, gt=0, description="Max nightly price in INR"),
    amenity: Optional[str] = Query(None, description="Specific amenity required"),
    db: Session = Depends(get_db)
):
    """Retrieves simulated hotels with optional filtering."""
    query = db.query(Hotel)
    
    if city:
        query = query.filter(func.lower(Hotel.city) == city.strip().lower())
    if star_rating is not None:
        query = query.filter(Hotel.star_rating == star_rating)
    if max_price is not None:
        query = query.filter(Hotel.price_per_night <= max_price)

    hotels = query.order_by(Hotel.price_per_night.asc()).all()
    
    if amenity:
        amenity_lower = amenity.strip().lower()
        hotels = [h for h in hotels if any(amenity_lower in a.lower() for a in (h.amenities or []))]

    return hotels
