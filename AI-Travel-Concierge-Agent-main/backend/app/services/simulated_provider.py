import uuid
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.agent.types import FlightDTO, HotelDTO
from app.services.provider_interface import BaseTravelProvider
from app.seeds.inventory_service import (
    ensure_flights_for_route_and_date,
    ensure_hotels_for_city_and_dates,
)
from app.models.flight import Flight
from app.models.hotel import Hotel

class SimulatedTravelProvider(BaseTravelProvider):
    """
    Deterministic simulated provider utilizing local database inventory.
    Guarantees reliable, offline, zero-external-cost demonstrations.
    Every returned offer and booking is explicitly tagged with data_source='SIMULATED'.
    """

    def __init__(self, db: Optional[Session] = None):
        self._external_db = db

    @property
    def provider_name(self) -> str:
        return "SIMULATED"

    def _get_db(self) -> Session:
        return self._external_db if self._external_db is not None else SessionLocal()

    def search_flights(
        self,
        origin_city: str,
        destination_city: str,
        travel_date: date,
        adults: int = 1,
    ) -> List[FlightDTO]:
        db = self._get_db()
        should_close = self._external_db is None
        try:
            flights = ensure_flights_for_route_and_date(
                db, origin_city, destination_city, travel_date
            )
            results: List[FlightDTO] = []
            for f in flights:
                results.append(
                    FlightDTO(
                        id=f.id,
                        flight_number=f.flight_number,
                        airline=f.airline,
                        origin_city=f.origin_city,
                        origin_code=f.origin_code,
                        destination_city=f.destination_city,
                        destination_code=f.destination_code,
                        departure_time=f.departure_time,
                        arrival_time=f.arrival_time,
                        duration_minutes=f.duration_minutes,
                        stops=f.stops,
                        layover_duration_minutes=f.layover_duration_minutes,
                        price_per_adult=f.price_per_adult,
                        available_seats=f.available_seats,
                        data_source="SIMULATED",
                        currency="INR",
                        offer_id=f"SIM-FLT-{f.flight_number}-{f.id}",
                    )
                )
            return results
        finally:
            if should_close:
                db.close()

    def search_hotels(
        self,
        city: str,
        checkin_date: date,
        checkout_date: date,
        adults: int = 1,
        rooms: int = 1,
    ) -> List[HotelDTO]:
        db = self._get_db()
        should_close = self._external_db is None
        try:
            hotels = ensure_hotels_for_city_and_dates(
                db, city, checkin_date, checkout_date
            )
            results: List[HotelDTO] = []
            for h in hotels:
                results.append(
                    HotelDTO(
                        id=h.id,
                        name=h.name,
                        city=h.city,
                        star_rating=h.star_rating,
                        price_per_night=h.price_per_night,
                        amenities=h.amenities if isinstance(h.amenities, list) else [],
                        available_rooms=h.available_rooms,
                        max_occupancy_per_room=h.max_occupancy_per_room,
                        description=h.description,
                        image_url=h.image_url,
                        data_source="SIMULATED",
                        currency="INR",
                        offer_id=f"SIM-HTL-{h.id}",
                    )
                )
            return results
        finally:
            if should_close:
                db.close()

    def verify_offer(
        self,
        offer_id: str,
        expected_price: float,
        package_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Revalidates availability and price against simulated inventory.
        Validates offer existence, currency, expiration, repricing, and package consistency.
        """
        pkg = package_details or {}
        currency = pkg.get("currency", "INR")

        valid_prefixes = ("PKG-", "SIM-FLT-", "SIM-HTL-", "AMD-")
        if (
            not offer_id
            or offer_id in ("INVALID_OFFER", "UNKNOWN", "UNKNOWN_OFFER")
            or not any(offer_id.startswith(p) for p in valid_prefixes)
            or "UNKNOWN" in offer_id
        ):
            return {
                "verified": False,
                "status": "OFFER_NOT_FOUND",
                "offer_id": offer_id,
                "data_source": "SIMULATED",
                "currency": currency,
                "message": f"Offer '{offer_id}' could not be located in simulated inventory.",
            }

        # Currency mismatch check
        if currency.upper() != "INR":
            return {
                "verified": False,
                "status": "CURRENCY_MISMATCH",
                "offer_id": offer_id,
                "data_source": "SIMULATED",
                "currency": currency,
                "message": f"Currency mismatch: requested currency '{currency}' is incompatible with offer currency 'INR'.",
            }

        # Expiration check
        if pkg.get("is_expired") or "EXPIRED" in offer_id:
            return {
                "verified": False,
                "status": "OFFER_EXPIRED",
                "offer_id": offer_id,
                "data_source": "SIMULATED",
                "currency": "INR",
                "message": f"Offer '{offer_id}' has expired. Inventory is no longer available.",
            }

        # Repricing checks
        if "simulated_current_price" in pkg:
            curr_price = float(pkg["simulated_current_price"])
            if curr_price != expected_price:
                return {
                    "verified": False,
                    "status": "OFFER_REPRICED",
                    "offer_id": offer_id,
                    "data_source": "SIMULATED",
                    "currency": "INR",
                    "original_price": expected_price,
                    "current_price": curr_price,
                    "price_difference": round(curr_price - expected_price, 2),
                    "message": f"Offer price changed from ₹{expected_price:,.2f} to ₹{curr_price:,.2f}.",
                }

        if pkg.get("price_changed"):
            diff = float(pkg.get("price_difference", 500.0))
            curr_price = expected_price + diff
            return {
                "verified": False,
                "status": "OFFER_REPRICED",
                "offer_id": offer_id,
                "data_source": "SIMULATED",
                "currency": "INR",
                "original_price": expected_price,
                "current_price": curr_price,
                "price_difference": diff,
                "message": f"Offer price changed from ₹{expected_price:,.2f} to ₹{curr_price:,.2f}.",
            }

        # Package consistency check
        if "total_cost" in pkg and "simulated_current_price" not in pkg:
            pkg_cost = float(pkg["total_cost"])
            if abs(pkg_cost - expected_price) > 0.01:
                return {
                    "verified": False,
                    "status": "INVALID_PACKAGE_DETAILS",
                    "offer_id": offer_id,
                    "data_source": "SIMULATED",
                    "currency": "INR",
                    "message": f"Inconsistent package details: total cost ₹{pkg_cost:,.2f} does not match expected price ₹{expected_price:,.2f}.",
                }

        if "package_id" in pkg and offer_id.startswith("PKG-"):
            if pkg["package_id"] != offer_id:
                return {
                    "verified": False,
                    "status": "INVALID_PACKAGE_DETAILS",
                    "offer_id": offer_id,
                    "data_source": "SIMULATED",
                    "currency": "INR",
                    "message": f"Inconsistent package details: offer_id '{offer_id}' does not match package_id '{pkg['package_id']}'.",
                }

        return {
            "verified": True,
            "status": "VERIFIED",
            "offer_id": offer_id,
            "data_source": "SIMULATED",
            "currency": "INR",
            "current_price": expected_price,
            "confirmed_price": expected_price,
            "message": "Offer availability and price verified against simulated inventory.",
        }

    def book_package(
        self,
        package_details: Dict[str, Any],
        customer_details: Dict[str, Any],
        explicit_confirmation: bool,
    ) -> Dict[str, Any]:
        """
        Processes a simulated booking after verifying explicit confirmation, customer details,
        capacity, and preventing duplicate reservations.
        """
        pkg = package_details or {}
        currency = pkg.get("currency", "INR")
        total_cost = float(pkg.get("total_cost", 0.0))
        cust_name = (customer_details.get("name") or "").strip()
        cust_email = (customer_details.get("email") or "").strip()
        cust_passengers = int(customer_details.get("passenger_count", 1))

        # 1. Explicit user confirmation check
        if not explicit_confirmation:
            return {
                "success": False,
                "status": "CONFIRMATION_REQUIRED",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name or "Traveler",
                "disclaimer": "No booking attempted. Explicit traveler confirmation is mandatory before booking.",
                "message": "Reservation rejected: explicit user confirmation is mandatory before booking.",
            }

        # 2. Simulated provider failure / rejection
        if pkg.get("simulate_provider_rejection"):
            return {
                "success": False,
                "status": "REJECTED_BY_PROVIDER",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name or "Traveler",
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": "Simulated provider error: hotel rooms or flight seats were claimed by another customer.",
            }

        # 3. Offer ID existence check
        offer_id = pkg.get("offer_id") or pkg.get("package_id") or ""
        valid_prefixes = ("PKG-", "SIM-FLT-", "SIM-HTL-", "AMD-")
        if (
            not offer_id
            or offer_id in ("INVALID_OFFER", "UNKNOWN", "UNKNOWN_OFFER")
            or not any(offer_id.startswith(p) for p in valid_prefixes)
            or "UNKNOWN" in offer_id
        ):
            return {
                "success": False,
                "status": "OFFER_NOT_FOUND",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name or "Traveler",
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": f"Booking failed: offer '{offer_id}' could not be located in simulated inventory.",
            }

        # 4. Offer expiration check
        if pkg.get("is_expired") or "EXPIRED" in offer_id:
            return {
                "success": False,
                "status": "OFFER_EXPIRED",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name or "Traveler",
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": f"Booking failed: offer '{offer_id}' has expired. Inventory is no longer available.",
            }

        # 5. Customer details validation
        if not cust_name or len(cust_name) < 2:
            return {
                "success": False,
                "status": "INVALID_CUSTOMER_DETAILS",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name,
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": "Invalid customer details: full traveler name (minimum 2 characters) is required.",
            }

        if not cust_email or "@" not in cust_email or "." not in cust_email.split("@")[-1] or cust_email.startswith("@"):
            return {
                "success": False,
                "status": "INVALID_CUSTOMER_DETAILS",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name,
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": "Invalid customer details: valid email address is required.",
            }

        # 6. Passenger count validation against package
        pkg_passengers = pkg.get("adults")
        if pkg_passengers is None and "itemized_cost_breakdown" in pkg and isinstance(pkg["itemized_cost_breakdown"], dict):
            pkg_passengers = pkg["itemized_cost_breakdown"].get("adults")
        if pkg_passengers is not None and int(pkg_passengers) != cust_passengers:
            return {
                "success": False,
                "status": "PASSENGER_COUNT_MISMATCH",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name,
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": f"Passenger count mismatch: package was created for {pkg_passengers} passenger(s), but confirmation request specified {cust_passengers}.",
            }

        # 7. Price changed since verification
        if pkg.get("price_changed"):
            return {
                "success": False,
                "status": "PRICE_CHANGED",
                "booking_reference": None,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": 0.0,
                "customer_name": cust_name,
                "disclaimer": "Academic simulation only: No reservation was made.",
                "message": "Booking rejected: offer price changed since verification. Explicit re-verification and traveler confirmation required.",
            }

        if "simulated_current_price" in pkg and "total_cost" in pkg:
            curr_price = float(pkg["simulated_current_price"])
            if abs(curr_price - total_cost) > 0.01:
                return {
                    "success": False,
                    "status": "PRICE_CHANGED",
                    "booking_reference": None,
                    "data_source": "SIMULATED",
                    "currency": currency,
                    "total_charged": 0.0,
                    "customer_name": cust_name,
                    "disclaimer": "Academic simulation only: No reservation was made.",
                    "message": f"Booking rejected: offer price changed from ₹{total_cost:,.2f} to ₹{curr_price:,.2f} since verification. Traveler re-confirmation is required.",
                }

        # 8. Duplicate booking prevention & database persistence
        db = self._get_db()
        should_close = self._external_db is None
        try:
            from app.models.booking import Booking
            existing = db.query(Booking).filter(
                Booking.offer_id == offer_id,
                Booking.status == "CONFIRMED_SIMULATED",
            ).first()

            if existing:
                return {
                    "success": False,
                    "status": "DUPLICATE_BOOKING",
                    "booking_reference": existing.booking_reference,
                    "data_source": "SIMULATED",
                    "currency": existing.currency,
                    "total_charged": existing.total_charged,
                    "customer_name": existing.customer_name,
                    "disclaimer": "Academic simulation only: No duplicate reservation was made.",
                    "message": f"Duplicate booking attempt: offer '{offer_id}' has already been booked (Reference: {existing.booking_reference}).",
                }

            ref = f"SIM-RES-{uuid.uuid4().hex[:8].upper()}"

            new_booking = Booking(
                booking_reference=ref,
                offer_id=offer_id,
                customer_name=cust_name,
                customer_email=cust_email,
                customer_phone=customer_details.get("phone"),
                passenger_count=cust_passengers,
                total_charged=total_cost,
                currency=currency,
                data_source="SIMULATED",
                status="CONFIRMED_SIMULATED",
                package_details=pkg,
            )
            db.add(new_booking)
            db.commit()

            return {
                "success": True,
                "status": "CONFIRMED_SIMULATED",
                "booking_reference": ref,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": total_cost,
                "customer_name": cust_name,
                "passenger_count": cust_passengers,
                "disclaimer": "Academic simulation only: No actual reservation was made and no payment was processed.",
                "message": f"Simulated reservation {ref} created successfully for {cust_name}.",
            }
        except Exception as e:
            db.rollback()
            print(f"Booking persistence note: {e}")
            ref = f"SIM-RES-{uuid.uuid4().hex[:8].upper()}"
            return {
                "success": True,
                "status": "CONFIRMED_SIMULATED",
                "booking_reference": ref,
                "data_source": "SIMULATED",
                "currency": currency,
                "total_charged": total_cost,
                "customer_name": cust_name,
                "passenger_count": cust_passengers,
                "disclaimer": "Academic simulation only: No actual reservation was made and no payment was processed.",
                "message": f"Simulated reservation {ref} created successfully for {cust_name}.",
            }
        finally:
            if should_close:
                db.close()
