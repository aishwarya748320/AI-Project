import pytest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
import requests

from app.services.amadeus_provider import AmadeusTravelProvider

class TestAmadeusProviderAdapter:
    """
    Mock-based unit tests for the Amadeus travel provider adapter.
    Validates OAuth2 token acquisition, timeout/rate-limit handling, flight search parsing,
    offer revalidation, and explicit confirmation enforcement without requiring real internet or credentials.
    """

    def test_unconfigured_provider_falls_back(self):
        provider = AmadeusTravelProvider(client_id="", client_secret="")
        assert not provider.is_configured
        flights = provider.search_flights("Delhi", "Mumbai", date(2026, 11, 10), adults=1)
        assert len(flights) > 0
        assert flights[0].data_source == "SIMULATED"

    @patch("requests.post")
    def test_authentication_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_test_token_12345",
            "expires_in": 1799,
        }
        mock_post.return_value = mock_resp

        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        token = provider._authenticate()
        assert token == "mock_test_token_12345"
        assert provider._get_auth_headers()["Authorization"] == "Bearer mock_test_token_12345"

    @patch("requests.post")
    def test_authentication_invalid_credentials_401(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        provider = AmadeusTravelProvider(client_id="bad_id", client_secret="bad_secret")
        with pytest.raises(PermissionError) as exc_info:
            provider._authenticate()
        assert "Invalid Client ID or Secret" in str(exc_info.value)

    @patch("requests.post")
    def test_authentication_rate_limit_429(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Too Many Requests"
        mock_post.return_value = mock_resp

        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        with pytest.raises(RuntimeError) as exc_info:
            provider._authenticate()
        assert "rate limit exceeded" in str(exc_info.value)

    @patch("requests.post")
    def test_authentication_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        with pytest.raises(TimeoutError) as exc_info:
            provider._authenticate()
        assert "timed out" in str(exc_info.value)

    @patch.object(AmadeusTravelProvider, "_get_auth_headers")
    @patch("requests.get")
    def test_flight_search_parsing_success(self, mock_get, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer mock_token"}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "1",
                    "numberOfBookableSeats": 5,
                    "price": {"total": "12000.00", "currency": "INR"},
                    "itineraries": [
                        {
                            "segments": [
                                {
                                    "carrierCode": "6E",
                                    "number": "505",
                                    "departure": {"at": "2026-11-10T08:00:00"},
                                    "arrival": {"at": "2026-11-10T10:15:00"},
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_resp

        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        flights = provider.search_flights("Delhi", "Mumbai", date(2026, 11, 10), adults=2)

        assert len(flights) == 1
        flight = flights[0]
        assert flight.flight_number == "6E-505"
        assert flight.airline == "6E"
        assert flight.data_source == "AMADEUS_API"
        assert flight.price_per_adult == 6000.0
        assert flight.available_seats == 5
        assert flight.stops == 0

    @patch.object(AmadeusTravelProvider, "_get_auth_headers")
    @patch("requests.post")
    def test_verify_offer_pricing_detection(self, mock_post, mock_headers):
        mock_headers.return_value = {"Authorization": "Bearer mock_token"}
        
        # Test 1: Repriced offer
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "flightOffers": [
                    {"price": {"total": "14500.00"}}
                ]
            }
        }
        mock_post.return_value = mock_resp

        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        result = provider.verify_offer(
            offer_id="AMD-FLT-1",
            expected_price=12000.0,
            package_details={"amadeus_offer_data": {"id": "1"}}
        )
        assert result["verified"] is False
        assert result["status"] == "OFFER_REPRICED"
        assert result["current_price"] == 14500.0
        assert result["price_difference"] == 2500.0

    def test_booking_requires_explicit_confirmation(self):
        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        res = provider.book_package(
            package_details={"total_cost": 50000.0},
            customer_details={"name": "Kanakachala"},
            explicit_confirmation=False,
        )
        assert res["success"] is False
        assert res["status"] == "CONFIRMATION_REQUIRED"

    def test_booking_sandbox_with_explicit_confirmation(self):
        provider = AmadeusTravelProvider(client_id="mock_id", client_secret="mock_secret")
        res = provider.book_package(
            package_details={"total_cost": 50000.0},
            customer_details={"name": "Kanakachala"},
            explicit_confirmation=True,
        )
        assert res["success"] is True
        assert res["status"] == "CONFIRMED_SANDBOX"
        assert res["data_source"] == "AMADEUS_API"
        assert "disclaimer" in res
