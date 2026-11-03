from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, JSON, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False, index=True)
    star_rating = Column(Integer, nullable=False, index=True)
    price_per_night = Column(Float, nullable=False)
    
    # List of amenities e.g. ["Free WiFi", "Swimming Pool", "Complimentary Breakfast", "Spa", "Airport Transfer", "Fitness Center"]
    amenities = Column(JSON, nullable=False, default=list)
    
    available_rooms = Column(Integer, default=10, nullable=False)
    max_occupancy_per_room = Column(Integer, default=2, nullable=False)
    
    image_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)

    # Date-specific room availability relationship
    daily_availabilities = relationship("HotelAvailability", back_populates="hotel", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Hotel {self.name} ({self.city}, {self.star_rating}★) ₹{self.price_per_night}/night>"


class HotelAvailability(Base):
    __tablename__ = "hotel_availabilities"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    rooms_available = Column(Integer, default=10, nullable=False)

    hotel = relationship("Hotel", back_populates="daily_availabilities")

    def __repr__(self):
        return f"<HotelAvailability hotel_id={self.hotel_id} date={self.date} rooms={self.rooms_available}>"
