import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.seeds.run_seed import seed_database

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Ensure database has clean seeded records for integration testing."""
    seed_database(clear_existing=True)

@pytest.fixture
def client():
    return TestClient(app)

class TestHealthAndInventoryAPI:
    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert data["database"] == "healthy"

    def test_flights_endpoint(self, client):
        response = client.get("/api/flights")
        assert response.status_code == 200
        flights = response.json()
        assert len(flights) >= 25
        
        # Test filtering by origin and destination
        resp_filtered = client.get("/api/flights?origin=Delhi&destination=Mumbai")
        assert resp_filtered.status_code == 200
        del_bom_flights = resp_filtered.json()
        assert len(del_bom_flights) >= 4
        for f in del_bom_flights:
            assert f["origin_city"] == "Delhi"
            assert f["destination_city"] == "Mumbai"

    def test_hotels_endpoint(self, client):
        response = client.get("/api/hotels")
        assert response.status_code == 200
        hotels = response.json()
        assert len(hotels) >= 15

        # Test filtering by city and star rating
        resp_filtered = client.get("/api/hotels?city=Mumbai&star_rating=5")
        assert resp_filtered.status_code == 200
        mumbai_5stars = resp_filtered.json()
        assert len(mumbai_5stars) >= 2
        for h in mumbai_5stars:
            assert h["city"] == "Mumbai"
            assert h["star_rating"] == 5


class TestRecommendationScenarios:
    def test_scenario_1_tight_budget(self, client):
        """Scenario 1: Find the cheapest valid round-trip package under a tight budget."""
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 1,
            "budget": 25000.0,
            "preferred_hotel_stars": 3,
            "hotel_category_is_hard": True,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["best_package"] is not None
        
        best = data["best_package"]
        assert best["hotel"]["star_rating"] == 3
        assert best["total_cost"] <= 25000.0
        assert best["remaining_budget"] >= 0.0
        assert best["outbound_flight"]["origin_city"] == "Delhi"
        assert best["return_flight"]["origin_city"] == "Mumbai"
        assert "lowest total cost" in data["explanation"].lower()
        
        # Test persistence retrieval by returned ID
        search_id = data["id"]
        assert search_id is not None
        get_res = client.get(f"/api/recommendations/{search_id}")
        assert get_res.status_code == 200
        assert get_res.json()["id"] == search_id

    def test_scenario_2_luxury_trip(self, client):
        """Scenario 2: Luxury trip with strict 5-star hotel requirement and sufficient budget."""
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 2,
            "budget": 150000.0,
            "preferred_hotel_stars": 5,
            "hotel_category_is_hard": True,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        best = data["best_package"]
        assert best["hotel"]["star_rating"] == 5
        assert best["total_cost"] <= 150000.0

    def test_scenario_3_infeasible_budget(self, client):
        """Scenario 3: Infeasible trip with an impossible budget yields clear explanation and suggestions."""
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 2,
            "budget": 3000.0,  # Far below minimum flight + hotel cost
            "preferred_hotel_stars": 3,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NO_FEASIBLE_PACKAGE"
        assert data["best_package"] is None
        assert len(data["actionable_suggestions"]) > 0
        assert "budget" in data["explanation"].lower()


class TestEdgeCasesAndValidation:
    def test_invalid_dates_return_before_departure(self, client):
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-14",
            "return_date": "2026-11-10",
            "adults": 1,
            "budget": 20000.0,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "INVALID_INPUT"
        assert "cannot precede" in data["explanation"].lower()

    def test_same_origin_and_destination(self, client):
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Delhi",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 1,
            "budget": 20000.0,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "INVALID_INPUT"
        assert "cannot both be" in data["explanation"].lower()

    def test_negative_budget_validation_error(self, client):
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 1,
            "budget": -500.0,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 422  # Pydantic validation error

    def test_nonexistent_recommendation_id(self, client):
        response = client.get("/api/recommendations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        assert "not found" in response.json()["message"].lower()

    def test_history_list_endpoint(self, client):
        response = client.get("/api/recommendations/history")
        assert response.status_code == 200
        history = response.json()
        assert isinstance(history, list)
        assert len(history) >= 1

    def test_api_response_utf8_encoding_rupee_and_star_symbols(self, client):
        """
        Regression test: Verify API returns clean UTF-8 encoded JSON with valid rupee (₹)
        and star (★) unicode characters without replacement characters (\ufffd).
        """
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 2,
            "budget": 50000.0,
            "preferred_hotel_stars": 3,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

        # Verify raw bytes contain exact UTF-8 sequences for ₹ (0xE2 0x82 0xB9) and ★ (0xE2 0x98 0x85)
        assert b"\xe2\x82\xb9" in response.content, "Rupee symbol byte sequence missing in response body"
        assert b"\xe2\x98\x85" in response.content, "Star symbol byte sequence missing in response body"

        # Verify parsed JSON text contains unicode glyphs without replacement character
        assert "\ufffd" not in response.text, "Corrupt replacement character detected in response"
        data = response.json()
        assert "₹" in data["explanation"]
        assert "★" in data["explanation"]

    def test_infeasible_api_response_tailored_suggestions_and_encoding(self, client):
        """
        Regression test: Verify that an infeasible-budget API response with hard 3-star constraint
        delivers tailored suggestions without redundant 3-star/4-star suggestions and with valid UTF-8 symbols.
        """
        payload = {
            "departure_city": "Delhi",
            "destination_city": "Mumbai",
            "departure_date": "2026-11-10",
            "return_date": "2026-11-14",
            "adults": 2,
            "budget": 3000.0,
            "preferred_hotel_stars": 3,
            "hotel_category_is_hard": True,
        }
        response = client.post("/api/recommendations", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "NO_FEASIBLE_PACKAGE"
        assert len(data["actionable_suggestions"]) > 0

        suggestions_str = " ".join(data["actionable_suggestions"])
        assert "3★ or 4★" not in suggestions_str
        assert "select a 3★" not in suggestions_str
        assert "select a 4★" not in suggestions_str
        assert "Flexible Hotel Category" in suggestions_str
        assert "₹" in suggestions_str
        assert "\ufffd" not in response.text
