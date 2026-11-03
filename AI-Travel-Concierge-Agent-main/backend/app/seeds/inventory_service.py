import random
from datetime import datetime, date, timedelta, time
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.flight import Flight
from app.models.hotel import Hotel, HotelAvailability
from app.seeds.seed_data import AIRPORT_CODES

# Default realistic hotel templates for supported Indian cities
CITY_HOTEL_TEMPLATES = {
    "Kolkata": [
        {
            "name": "Hotel Lindsay New Market",
            "star_rating": 3,
            "price_per_night": 2500.0,
            "amenities": ["Free WiFi", "Breakfast Included", "Air Conditioning", "Restaurant"],
            "available_rooms": 14,
            "max_occupancy_per_room": 2,
            "description": "Centrally located heritage-style hotel facing the historic New Market.",
        },
        {
            "name": "The Peerless Inn Kolkata",
            "star_rating": 4,
            "price_per_night": 5200.0,
            "amenities": ["Free WiFi", "Fitness Center", "Multi-Cuisine Dining", "Airport Shuttle"],
            "available_rooms": 10,
            "max_occupancy_per_room": 2,
            "description": "Refined 4-star property near Esplanade with renowned Bengali cuisine.",
        },
        {
            "name": "The Oberoi Grand Kolkata",
            "star_rating": 5,
            "price_per_night": 18500.0,
            "amenities": ["Free WiFi", "Swimming Pool", "Luxury Spa", "Fine Dining", "Valet"],
            "available_rooms": 8,
            "max_occupancy_per_room": 2,
            "description": "The Grande Dame of Chowringhee, colonial palatial luxury with lush courtyards.",
        },
    ],
    "Chennai": [
        {
            "name": "Hotel Pandian Egmore",
            "star_rating": 3,
            "price_per_night": 2400.0,
            "amenities": ["Free WiFi", "Breakfast Included", "Air Conditioning"],
            "available_rooms": 12,
            "max_occupancy_per_room": 2,
            "description": "Comfortable stay close to Chennai Central and cultural venues.",
        },
        {
            "name": "The Residency Towers T Nagar",
            "star_rating": 4,
            "price_per_night": 5100.0,
            "amenities": ["Free WiFi", "Swimming Pool", "Spa", "Fitness Center", "Bar"],
            "available_rooms": 9,
            "max_occupancy_per_room": 2,
            "description": "Upscale hotel in Chennai's commercial hub.",
        },
        {
            "name": "The Leela Palace Chennai",
            "star_rating": 5,
            "price_per_night": 19500.0,
            "amenities": ["Free WiFi", "Sea View", "Swimming Pool", "ESPA Spa", "Fine Dining"],
            "available_rooms": 6,
            "max_occupancy_per_room": 2,
            "description": "Chettinad palace-inspired oceanfront luxury overlooking the Bay of Bengal.",
        },
    ],
    "Hyderabad": [
        {
            "name": "Treebo Trend Inner Circle",
            "star_rating": 3,
            "price_per_night": 2500.0,
            "amenities": ["Free WiFi", "Breakfast Included", "Air Conditioning"],
            "available_rooms": 15,
            "max_occupancy_per_room": 2,
            "description": "Clean modern hotel in Somajiguda.",
        },
        {
            "name": "Lemon Tree Premier Hitec City",
            "star_rating": 4,
            "price_per_night": 5500.0,
            "amenities": ["Free WiFi", "Swimming Pool", "Spa", "Fitness Center", "Restaurant"],
            "available_rooms": 11,
            "max_occupancy_per_room": 2,
            "description": "Vibrant business hotel in the heart of Hyderabad's cyber corridor.",
        },
        {
            "name": "Taj Falaknuma Palace",
            "star_rating": 5,
            "price_per_night": 32000.0,
            "amenities": ["Free WiFi", "Heritage Palace Tour", "Swimming Pool", "Jiva Spa", "Royal Dining"],
            "available_rooms": 4,
            "max_occupancy_per_room": 2,
            "description": "The Mirror of the Sky: authentic Nizam palace situated 2,000 feet above Hyderabad.",
        },
    ],
}

def ensure_flights_for_route_and_date(
    db: Session,
    origin_city: str,
    dest_city: str,
    target_date: date
) -> List[Flight]:
    """
    Checks if flights exist for the given origin, destination, and date.
    If none exist and both cities are in our supported Indian airport network,
    generates realistic flights and persists them.
    """
    existing = db.query(Flight).filter(
        func.lower(Flight.origin_city) == origin_city.strip().lower(),
        func.lower(Flight.destination_city) == dest_city.strip().lower(),
        func.date(Flight.departure_time) == target_date
    ).all()

    if existing:
        return existing

    # Only generate flights between supported network cities
    supported_cities = {k.lower(): k for k in AIRPORT_CODES.keys()}
    origin_key = supported_cities.get(origin_city.strip().lower())
    dest_key = supported_cities.get(dest_city.strip().lower())

    if not origin_key or not dest_key:
        return []

    origin_code = AIRPORT_CODES[origin_key]
    dest_code = AIRPORT_CODES[dest_key]

    # Generate 4 diverse flight options
    flight_configs = [
        ("IndiGo", f"6E-{random.randint(1100, 9999)}", time(6, 30), 150, 0, 0, 4300.0, 25),
        ("Air India", f"AI-{random.randint(400, 999)}", time(10, 45), 155, 0, 0, 5200.0, 18),
        ("SpiceJet", f"SG-{random.randint(100, 899)}", time(13, 15), 275, 1, 75, 3650.0, 14),
        ("Akasa Air", f"QP-{random.randint(1100, 1999)}", time(18, 20), 150, 0, 0, 4400.0, 20),
    ]

    new_flights = []
    for airline, num, dep_t, duration, stops, layover, price, seats in flight_configs:
        dep_dt = datetime.combine(target_date, dep_t)
        arr_dt = dep_dt + timedelta(minutes=duration)
        flight = Flight(
            flight_number=num,
            airline=airline,
            origin_city=origin_key,
            origin_code=origin_code,
            destination_city=dest_key,
            destination_code=dest_code,
            departure_time=dep_dt,
            arrival_time=arr_dt,
            duration_minutes=duration,
            stops=stops,
            layover_duration_minutes=layover,
            price_per_adult=price,
            available_seats=seats,
        )
        db.add(flight)
        new_flights.append(flight)

    db.commit()
    return new_flights


def ensure_hotels_for_city_and_dates(
    db: Session,
    dest_city: str,
    check_in: date,
    check_out: date
) -> List[Hotel]:
    """
    Ensures the destination city has hotels and room availability for the requested date window.
    """
    city_lower = dest_city.strip().lower()
    existing_hotels = db.query(Hotel).filter(func.lower(Hotel.city) == city_lower).all()

    # Only generate hotels for supported network cities
    supported_cities = {k.lower(): k for k in AIRPORT_CODES.keys()}
    city_key = supported_cities.get(city_lower)

    if not city_key:
        return []

    # If no hotels exist for this city, create them
    if not existing_hotels:
        templates = CITY_HOTEL_TEMPLATES.get(city_key, [])
        if not templates:
            templates = [
                {
                    "name": f"FabHotel Central {city_key}",
                    "star_rating": 3,
                    "price_per_night": 2600.0,
                    "amenities": ["Free WiFi", "Breakfast Included", "Air Conditioning"],
                    "available_rooms": 12,
                    "max_occupancy_per_room": 2,
                    "description": f"Comfortable budget accommodation in {city_key}.",
                },
                {
                    "name": f"Lemon Tree Hotel {city_key}",
                    "star_rating": 4,
                    "price_per_night": 5400.0,
                    "amenities": ["Free WiFi", "Swimming Pool", "Fitness Center", "Restaurant"],
                    "available_rooms": 10,
                    "max_occupancy_per_room": 2,
                    "description": f"Upscale hotel offering contemporary rooms in {city_key}.",
                },
                {
                    "name": f"The Taj Palace {city_key}",
                    "star_rating": 5,
                    "price_per_night": 21000.0,
                    "amenities": ["Free WiFi", "Swimming Pool", "Luxury Spa", "Fine Dining", "Valet"],
                    "available_rooms": 6,
                    "max_occupancy_per_room": 2,
                    "description": f"World-class 5-star luxury property in {city_key}.",
                },
            ]

        for h_data in templates:
            hotel = Hotel(
                name=h_data["name"],
                city=city_key,
                star_rating=h_data["star_rating"],
                price_per_night=h_data["price_per_night"],
                amenities=h_data["amenities"],
                available_rooms=h_data["available_rooms"],
                max_occupancy_per_room=h_data["max_occupancy_per_room"],
                description=h_data.get("description"),
            )
            db.add(hotel)
            db.flush()

            days_count = max(7, (check_out - check_in).days + 15)
            for d_idx in range(days_count):
                cur_date = check_in + timedelta(days=d_idx)
                avail = HotelAvailability(
                    hotel_id=hotel.id,
                    date=cur_date,
                    rooms_available=hotel.available_rooms
                )
                db.add(avail)

        db.commit()
        existing_hotels = db.query(Hotel).filter(func.lower(Hotel.city) == city_lower).all()

    return existing_hotels
