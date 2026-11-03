from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.flight import Flight
from app.schemas.flight import FlightOut

router = APIRouter(prefix="/flights", tags=["Flights"])

@router.get("", response_model=List[FlightOut])
def get_flights(
    origin: Optional[str] = Query(None, description="Origin city e.g. Delhi"),
    destination: Optional[str] = Query(None, description="Destination city e.g. Mumbai"),
    flight_date: Optional[date] = Query(None, alias="date", description="Flight departure date (YYYY-MM-DD)"),
    airline: Optional[str] = Query(None, description="Airline name"),
    max_stops: Optional[int] = Query(None, ge=0, description="Max stops"),
    db: Session = Depends(get_db)
):
    """Retrieves simulated flights with optional filtering."""
    query = db.query(Flight)
    
    if origin:
        query = query.filter(func.lower(Flight.origin_city) == origin.strip().lower())
    if destination:
        query = query.filter(func.lower(Flight.destination_city) == destination.strip().lower())
    if flight_date:
        query = query.filter(func.date(Flight.departure_time) == flight_date)
    if airline:
        query = query.filter(func.lower(Flight.airline) == airline.strip().lower())
    if max_stops is not None:
        query = query.filter(Flight.stops <= max_stops)

    return query.order_by(Flight.departure_time.asc()).all()
