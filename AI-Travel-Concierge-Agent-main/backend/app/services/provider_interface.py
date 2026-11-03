from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date
from app.agent.types import FlightDTO, HotelDTO

class BaseTravelProvider(ABC):
    """
    Abstract interface for flight and hotel travel providers.
    Supports search, offer revalidation, and explicit reservation workflows.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'SIMULATED', 'AMADEUS')."""
        pass

    @abstractmethod
    def search_flights(
        self,
        origin_city: str,
        destination_city: str,
        travel_date: date,
        adults: int = 1,
    ) -> List[FlightDTO]:
        """Search and normalize flight offers for a single leg."""
        pass

    @abstractmethod
    def search_hotels(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        adults: int = 1,
        rooms: int = 1,
    ) -> List[HotelDTO]:
        """Search and normalize hotel offers for a destination city and stay dates."""
        pass

    @abstractmethod
    def verify_offer(
        self,
        offer_id: str,
        expected_price: float,
        package_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Revalidates availability and price of a selected offer prior to reservation.
        Returns a verification record with 'verified': bool, current price, and status message.
        """
        pass

    @abstractmethod
    def book_package(
        self,
        package_details: Dict[str, Any],
        customer_details: Dict[str, Any],
        explicit_confirmation: bool,
    ) -> Dict[str, Any]:
        """
        Submits a reservation request only with explicit user confirmation.
        Returns booking reference, status, and clear data source indicator.
        """
        pass
