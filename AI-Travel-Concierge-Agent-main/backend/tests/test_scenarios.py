import pytest
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

@pytest.fixture
def client():
    return TestClient(app)

class TestSpecialScenariosAndFailures:
    def test_empty_search_results_unknown_city(self, client):
        """Empty search results when querying cities with no inventory."""
        payload = {
            "departure_city": "Nagpur",
            "destination_city": "Bhopal",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 1,
            "budget": 50000.0,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NO_FEASIBLE_PACKAGE"
        assert data["best_package"] is None
        assert "no compatible flights or hotels" in data["message"].lower()

    def test_insufficient_seats_edge_case(self, client):
        """Traveling with 100 adults exceeds simulated flight seat capacity."""
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 100,  # exceeds any single flight's seats
            "budget": 2000000.0,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NO_FEASIBLE_PACKAGE"
        assert data["rejection_summary"]["insufficient_flight_seats"] > 0

    def test_database_connection_failure_handling(self):
        """Simulate database connection failure and verify graceful 500 JSON error."""
        def failing_db():
            raise Exception("Simulated PostgreSQL connection failure: connection refused")

        app.dependency_overrides[get_db] = failing_db
        try:
            # Use raise_server_exceptions=False to receive the HTTP 500 response from FastAPI
            err_client = TestClient(app, raise_server_exceptions=False)
            response = err_client.get("/api/flights")
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "INTERNAL_ERROR"
            assert "server error" in data["message"].lower()
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_hotel_strict_category_mismatch(self, client):
        """When 5-star is strictly required for a small budget that can only afford 3-star."""
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 1,
            "budget": 25000.0,
            "preferred_hotel_stars": 5,
            "hotel_category_is_hard": True,  # strict
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        # 5-star Mumbai hotel is 21,500/night * 4 nights = 86,000 + flight > 25,000
        assert data["status"] == "NO_FEASIBLE_PACKAGE"
        assert data["rejection_summary"]["hotel_stars_mismatch"] > 0 or data["rejection_summary"]["budget_exceeded"] > 0
        assert "Flexible Hotel Category" in " ".join(data["actionable_suggestions"])
