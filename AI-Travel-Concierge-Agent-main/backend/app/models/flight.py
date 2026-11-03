from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database import Base

class Flight(Base):
    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)
    flight_number = Column(String(30), nullable=False, index=True)
    airline = Column(String(100), nullable=False)
    origin_city = Column(String(100), nullable=False, index=True)
    origin_code = Column(String(10), nullable=False)
    destination_city = Column(String(100), nullable=False, index=True)
    destination_code = Column(String(10), nullable=False)
    
    departure_time = Column(DateTime, nullable=False, index=True)
    arrival_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    
    stops = Column(Integer, default=0, nullable=False)
    layover_duration_minutes = Column(Integer, default=0, nullable=False)
    
    price_per_adult = Column(Float, nullable=False)
    available_seats = Column(Integer, default=20, nullable=False)

    def __repr__(self):
        return f"<Flight {self.flight_number} {self.origin_code}->{self.destination_code} ₹{self.price_per_adult}>"
