import sys
import os
from datetime import date, timedelta, datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import SessionLocal, init_db
from app.models.flight import Flight
from app.models.hotel import Hotel, HotelAvailability
from app.seeds.seed_data import generate_flight_seeds, generate_hotel_seeds

def seed_database(clear_existing: bool = True):
    """Initializes schema and populates simulated flights and hotels."""
    print("Initializing database tables...")
    init_db()

    db = SessionLocal()
    try:
        if clear_existing:
            print("Clearing existing simulated flight, hotel, and booking records...")
            from app.models.booking import Booking
            from app.models.recommendation import RecommendationHistory
            try:
                db.query(Booking).delete()
            except Exception:
                pass
            try:
                db.query(RecommendationHistory).delete()
            except Exception:
                pass
            db.query(HotelAvailability).delete()
            db.query(Hotel).delete()
            db.query(Flight).delete()
            db.commit()

        # Seed Flights
        flight_seeds = generate_flight_seeds()
        print(f"Seeding {len(flight_seeds)} flights...")
        for f_data in flight_seeds:
            flight = Flight(**f_data)
            db.add(flight)
        db.commit()

        # Seed Hotels
        hotel_seeds = generate_hotel_seeds()
        print(f"Seeding {len(hotel_seeds)} hotels...")
        
        # Populate daily availability for dates around Nov 2026 and current dates
        # Range: 2026-11-01 to 2026-12-01 (30 days)
        start_date = date(2026, 11, 1)
        
        for h_data in hotel_seeds:
            hotel = Hotel(**h_data)
            db.add(hotel)
            db.flush()  # get hotel.id

            # Seed daily availability
            for day_offset in range(35):
                cur_date = start_date + timedelta(days=day_offset)
                # By default, use hotel's available_rooms
                avail = HotelAvailability(
                    hotel_id=hotel.id,
                    date=cur_date,
                    rooms_available=hotel.available_rooms
                )
                db.add(avail)

        db.commit()
        print(f"Successfully seeded database! Total flights: {len(flight_seeds)}, Total hotels: {len(hotel_seeds)}")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
