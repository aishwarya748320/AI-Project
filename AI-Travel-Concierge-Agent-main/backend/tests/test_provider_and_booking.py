import pytest
from datetime import date
from starlette.testclient import TestClient

from app.main import app
from app.services import get_travel_provider
from app.services.simulated_provider import SimulatedTravelProvider
from app.seeds.run_seed import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database has clean seeded records for provider and booking testing."""
    seed_database(clear_existing=True)

client = TestClient(app)

class TestProviderAndBookingWorkflow:
    """
    Automated verification of the provider abstraction, offer revalidation,
    and safe explicit-confirmation booking workflow.
    """

    def test_provider_factory_and_defaults(self):
        provider = get_travel_provider()
        assert isinstance(provider, SimulatedTravelProvider)
        assert provider.provider_name == "SIMULATED"

    def test_simulated_provider_explicit_labels(self):
        provider = get_travel_provider()
        flights = provider.search_flights("Delhi", "Mumbai", date(2026, 11, 10), adults=2)
        assert len(flights) > 0
        for f in flights:
            assert f.data_source == "SIMULATED"
            assert f.currency == "INR"
            assert f.offer_id.startswith("SIM-FLT-")

        hotels = provider.search_hotels("Mumbai", date(2026, 11, 10), date(2026, 11, 14), adults=2)
        assert len(hotels) > 0
        for h in hotels:
            assert h.data_source == "SIMULATED"
            assert h.currency == "INR"
            assert h.offer_id.startswith("SIM-HTL-")

    def test_recommendation_and_search_packages_contain_itemized_breakdown_and_assumptions(self):
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 2,
            "budget": 60000.0,
            "preferred_hotel_stars": 3,
            "hotel_category_is_hard": True,
            "room_sharing": True,
        }

        # Test both /api/recommendations and /api/search-packages
        res1 = client.post("/api/recommendations", json=payload)
        res2 = client.post("/api/search-packages", json=payload)

        assert res1.status_code == 200
        assert res2.status_code == 200

        data1 = res1.json()
        data2 = res2.json()

        assert data1["status"] == "SUCCESS"
        assert data2["status"] == "SUCCESS"
        assert data1["data_source"] == "SIMULATED"
        assert data1["currency"] == "INR"
        assert data1["itemized_cost_breakdown"] is not None
        assert data1["itemized_cost_breakdown"]["adults"] == 2
        assert len(data1["assumptions"]) > 0

        # Verify best package contains itemized fields
        best_pkg = data1["best_package"]
        assert best_pkg["data_source"] == "SIMULATED"
        assert best_pkg["currency"] == "INR"
        assert best_pkg["package_id"].startswith("PKG-")
        assert len(best_pkg["assumptions"]) > 0

    def test_offer_verification_success(self):
        payload = {
            "offer_id": "SIM-FLT-6E-101-1",
            "expected_price": 7500.0,
            "currency": "INR",
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is True
        assert data["status"] == "VERIFIED"
        assert data["data_source"] == "SIMULATED"
        assert data["currency"] == "INR"

    def test_offer_verification_repriced(self):
        payload = {
            "offer_id": "SIM-FLT-6E-101-1",
            "expected_price": 7500.0,
            "currency": "INR",
            "package_details": {
                "simulated_current_price": 8200.0
            }
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["status"] == "OFFER_REPRICED"
        assert data["price_difference"] == 700.0

    def test_offer_verification_expired(self):
        payload = {
            "offer_id": "SIM-FLT-6E-101-1",
            "expected_price": 7500.0,
            "currency": "INR",
            "package_details": {
                "is_expired": True
            }
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["status"] == "OFFER_EXPIRED"

    def test_booking_rejected_without_explicit_confirmation(self):
        payload = {
            "offer_id": "PKG-6E-101-6E-102-1",
            "confirm": False,  # EXPLICIT CONFIRMATION IS MISSING
            "customer": {
                "name": "Kanakachala",
                "email": "kanakachala@example.com",
                "passenger_count": 2,
            },
            "package_details": {
                "total_cost": 24500.0,
                "currency": "INR"
            }
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "CONFIRMATION_REQUIRED"
        assert data["booking_reference"] is None
        assert "explicit confirmation" in data["message"].lower()

    def test_booking_confirmed_with_explicit_confirmation(self):
        payload = {
            "offer_id": "PKG-6E-101-6E-102-1",
            "confirm": True,  # EXPLICIT CONFIRMATION PROVIDED
            "customer": {
                "name": "Kanakachala",
                "email": "kanakachala@example.com",
                "passenger_count": 2,
            },
            "package_details": {
                "total_cost": 24500.0,
                "currency": "INR"
            }
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "CONFIRMED_SIMULATED"
        assert data["booking_reference"].startswith("SIM-RES-")
        assert data["data_source"] == "SIMULATED"
        assert data["total_charged"] == 24500.0
        assert "Academic simulation" in data["disclaimer"]

    def test_booking_rejected_by_provider(self):
        payload = {
            "offer_id": "PKG-6E-101-6E-102-1",
            "confirm": True,
            "customer": {
                "name": "Kanakachala",
                "email": "kanakachala@example.com",
                "passenger_count": 2,
            },
            "package_details": {
                "total_cost": 24500.0,
                "simulate_provider_rejection": True,
            }
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "REJECTED_BY_PROVIDER"
        assert data["booking_reference"] is None

    # --- Comprehensive Offer Verification Edge Cases ---

    def test_verify_offer_unknown_offer_id(self):
        payload = {
            "offer_id": "UNKNOWN-OFFER-9999",
            "expected_price": 10000.0,
            "currency": "INR",
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["status"] == "OFFER_NOT_FOUND"
        assert "not be located" in data["message"].lower()

    def test_verify_offer_missing_fields_validation_error(self):
        # Missing offer_id
        response = client.post("/api/verify-offer", json={"expected_price": 5000.0})
        assert response.status_code == 422

        # Negative expected price
        response = client.post("/api/verify-offer", json={"offer_id": "SIM-FLT-1", "expected_price": -100.0})
        assert response.status_code == 422

    def test_verify_offer_currency_mismatch(self):
        payload = {
            "offer_id": "SIM-FLT-6E-101-1",
            "expected_price": 7500.0,
            "currency": "USD",  # Mismatch with simulated INR
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["status"] == "CURRENCY_MISMATCH"
        assert "incompatible" in data["message"].lower()

    def test_verify_offer_inconsistent_package_details(self):
        payload = {
            "offer_id": "PKG-SG-162-SG-163-1",
            "expected_price": 25000.0,
            "currency": "INR",
            "package_details": {
                "package_id": "PKG-SG-162-SG-163-1",
                "total_cost": 45000.0,  # Inconsistent with expected_price 25000.0
            }
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["status"] == "INVALID_PACKAGE_DETAILS"
        assert "does not match" in data["message"].lower()

    def test_verify_offer_mismatched_package_id(self):
        payload = {
            "offer_id": "PKG-SG-162-SG-163-1",
            "expected_price": 25000.0,
            "currency": "INR",
            "package_details": {
                "package_id": "PKG-DIFFERENT-ID",
                "total_cost": 25000.0,
            }
        }
        response = client.post("/api/verify-offer", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["verified"] is False
        assert data["status"] == "INVALID_PACKAGE_DETAILS"

    # --- Comprehensive Booking Confirmation Edge Cases ---

    def test_booking_unknown_offer_rejected(self):
        payload = {
            "offer_id": "UNKNOWN-OFFER-8888",
            "confirm": True,
            "customer": {
                "name": "Synthetic Traveler",
                "email": "traveler@example.com",
                "passenger_count": 1,
            },
            "package_details": {"total_cost": 15000.0}
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "OFFER_NOT_FOUND"

    def test_booking_expired_offer_rejected(self):
        payload = {
            "offer_id": "PKG-EXPIRED-OFFER",
            "confirm": True,
            "customer": {
                "name": "Synthetic Traveler",
                "email": "traveler@example.com",
                "passenger_count": 1,
            },
            "package_details": {"total_cost": 15000.0, "is_expired": True}
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "OFFER_EXPIRED"

    def test_booking_invalid_customer_details_rejected(self):
        # Invalid email (no domain / malformed)
        payload = {
            "offer_id": "PKG-6E-101-6E-102-2",
            "confirm": True,
            "customer": {
                "name": "Valid Name",
                "email": "not-an-email",
                "passenger_count": 1,
            },
            "package_details": {"total_cost": 15000.0}
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "INVALID_CUSTOMER_DETAILS"

        # Short / empty name
        payload["customer"]["name"] = " "
        payload["customer"]["email"] = "valid@example.com"
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code in (200, 422)
        if response.status_code == 200:
            assert response.json()["success"] is False

    def test_booking_passenger_count_mismatch_rejected(self):
        payload = {
            "offer_id": "PKG-6E-101-6E-102-3",
            "confirm": True,
            "customer": {
                "name": "Synthetic Traveler",
                "email": "traveler@example.com",
                "passenger_count": 3,  # Mismatch with package adults=2
            },
            "package_details": {
                "total_cost": 25000.0,
                "adults": 2,
            }
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "PASSENGER_COUNT_MISMATCH"
        assert "passenger count mismatch" in data["message"].lower()

    def test_booking_price_changed_since_verification_rejected(self):
        payload = {
            "offer_id": "PKG-6E-101-6E-102-4",
            "confirm": True,
            "customer": {
                "name": "Synthetic Traveler",
                "email": "traveler@example.com",
                "passenger_count": 2,
            },
            "package_details": {
                "total_cost": 25000.0,
                "simulated_current_price": 28500.0,  # Price jumped
            }
        }
        response = client.post("/api/booking/confirm", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "PRICE_CHANGED"
        assert "price changed" in data["message"].lower()

    def test_booking_duplicate_booking_attempt_handled_safely(self):
        unique_offer = "PKG-UNIQUE-ONCE-ONLY-99"
        payload = {
            "offer_id": unique_offer,
            "confirm": True,
            "customer": {
                "name": "Repeat Traveler",
                "email": "repeat@example.com",
                "passenger_count": 1,
            },
            "package_details": {
                "total_cost": 18000.0,
                "currency": "INR",
            }
        }

        # First booking attempt succeeds
        res1 = client.post("/api/booking/confirm", json=payload)
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["success"] is True
        assert data1["status"] == "CONFIRMED_SIMULATED"
        booking_ref = data1["booking_reference"]
        assert booking_ref.startswith("SIM-RES-")

        # Second booking attempt with identical offer_id is safely detected as duplicate
        res2 = client.post("/api/booking/confirm", json=payload)
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["success"] is False
        assert data2["status"] == "DUPLICATE_BOOKING"
        assert data2["booking_reference"] == booking_ref
        assert "already been booked" in data2["message"].lower()

    # --- Full End-to-End Recommendation -> Verification -> Confirmation Workflow ---

    def test_end_to_end_recommendation_verification_and_booking_workflow(self):
        """
        Complete end-to-end integration scenario matching the prompt specifications:
        A. Health check
        B. Recommendation request (Delhi -> Mumbai, 2026-11-10 to 2026-11-14, 2 adults, budget 50,000, 3-star hard, stops soft)
        C. Offer verification with real package data
        D. Negative confirmation test (confirm: false)
        E. Booking confirmation with explicit confirmation (confirm: true)
        F. Duplicate submission protection
        """
        # Step A: Health Check
        health_res = client.get("/api/health")
        assert health_res.status_code == 200
        health_data = health_res.json()
        assert health_data["status"] == "online"
        assert health_data["database"] == "healthy"

        # Step B: Recommendation
        req_payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 2,
            "budget": 50000.0,
            "preferred_hotel_stars": 3,
            "hotel_category_is_hard": True,
            "max_flight_stops": 0,
            "max_flight_stops_is_hard": False,
            "preferred_amenities": ["Free WiFi"],
            "amenities_are_hard": False,
        }
        rec_res = client.post("/api/recommendations", json=req_payload)
        assert rec_res.status_code == 200
        rec_data = rec_res.json()

        assert rec_data["status"] == "SUCCESS"
        assert rec_data["data_source"] == "SIMULATED"
        assert rec_data["currency"] == "INR"
        assert rec_data["best_package"] is not None

        best_pkg = rec_data["best_package"]
        package_id = best_pkg["package_id"]
        total_cost = best_pkg["total_cost"]
        flight_cost = best_pkg["flight_cost"]
        hotel_cost = best_pkg["hotel_cost"]

        # Validate itemized total consistency
        assert round(flight_cost + hotel_cost, 2) == round(total_cost, 2)
        assert total_cost <= 50000.0
        assert best_pkg["hotel"]["star_rating"] == 3

        # Step C: Offer Verification with Real Package Data
        verify_payload = {
            "offer_id": package_id,
            "expected_price": total_cost,
            "currency": "INR",
            "package_details": best_pkg,
        }
        ver_res = client.post("/api/verify-offer", json=verify_payload)
        assert ver_res.status_code == 200
        ver_data = ver_res.json()

        assert ver_data["verified"] is True
        assert ver_data["status"] == "VERIFIED"
        assert ver_data["offer_id"] == package_id
        assert ver_data["data_source"] == "SIMULATED"
        assert ver_data["current_price"] == total_cost

        # Step D: Negative Confirmation (confirm: false)
        neg_booking_payload = {
            "offer_id": package_id,
            "confirm": False,  # Traveler has not clicked final confirm
            "customer": {
                "name": "Priya Sharma",
                "email": "priya.sharma@example.com",
                "phone": "+91-9876543210",
                "passenger_count": 2,
            },
            "package_details": best_pkg,
        }
        neg_res = client.post("/api/booking/confirm", json=neg_booking_payload)
        assert neg_res.status_code == 200
        neg_data = neg_res.json()

        assert neg_data["success"] is False
        assert neg_data["status"] == "CONFIRMATION_REQUIRED"
        assert neg_data["booking_reference"] is None
        assert "explicit confirmation" in neg_data["message"].lower()

        # Step E: Positive Confirmation (confirm: true)
        pos_booking_payload = dict(neg_booking_payload)
        pos_booking_payload["confirm"] = True

        pos_res = client.post("/api/booking/confirm", json=pos_booking_payload)
        assert pos_res.status_code == 200
        pos_data = pos_res.json()

        assert pos_data["success"] is True
        assert pos_data["status"] == "CONFIRMED_SIMULATED"
        assert pos_data["data_source"] == "SIMULATED"
        assert pos_data["currency"] == "INR"
        assert pos_data["total_charged"] == total_cost
        assert pos_data["customer_name"] == "Priya Sharma"

        booking_ref = pos_data["booking_reference"]
        assert booking_ref is not None
        assert booking_ref.startswith("SIM-RES-")
        assert "Academic simulation" in pos_data["disclaimer"]
        assert "No actual reservation was made" in pos_data["disclaimer"]

        # Step F: Duplicate Submission Protection
        dup_res = client.post("/api/booking/confirm", json=pos_booking_payload)
        assert dup_res.status_code == 200
        dup_data = dup_res.json()

        assert dup_data["success"] is False
        assert dup_data["status"] == "DUPLICATE_BOOKING"
        assert dup_data["booking_reference"] == booking_ref
        assert "already been booked" in dup_data["message"].lower()
