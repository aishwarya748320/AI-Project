import pytest
from datetime import date, datetime, timedelta
from app.agent.agent import ConciergeAgent
from app.agent.types import TravelRequirements, FlightDTO, HotelDTO, TravelPackage
from app.agent.constraints import calculate_rooms_required, check_hard_constraints
from app.agent.optimizer import sort_and_optimize_packages

# Sample flights fixtures
@pytest.fixture
def sample_flights():
    return [
        FlightDTO(
            id=1,
            flight_number="6E-101",
            airline="IndiGo",
            origin_city="Delhi",
            origin_code="DEL",
            destination_city="Mumbai",
            destination_code="BOM",
            departure_time=datetime(2026, 11, 10, 8, 0),
            arrival_time=datetime(2026, 11, 10, 10, 15),
            duration_minutes=135,
            stops=0,
            layover_duration_minutes=0,
            price_per_adult=4000.0,
            available_seats=10,
        ),
        FlightDTO(
            id=2,
            flight_number="SG-202",
            airline="SpiceJet",
            origin_city="Delhi",
            origin_code="DEL",
            destination_city="Mumbai",
            destination_code="BOM",
            departure_time=datetime(2026, 11, 10, 6, 0),
            arrival_time=datetime(2026, 11, 10, 10, 30),
            duration_minutes=270,
            stops=1,
            layover_duration_minutes=60,
            price_per_adult=3500.0,
            available_seats=5,
        ),
        FlightDTO(
            id=3,
            flight_number="6E-102",
            airline="IndiGo",
            origin_city="Mumbai",
            origin_code="BOM",
            destination_city="Delhi",
            destination_code="DEL",
            departure_time=datetime(2026, 11, 14, 18, 0),
            arrival_time=datetime(2026, 11, 14, 20, 15),
            duration_minutes=135,
            stops=0,
            layover_duration_minutes=0,
            price_per_adult=4200.0,
            available_seats=10,
        ),
        FlightDTO(
            id=4,
            flight_number="AI-303",
            airline="Air India",
            origin_city="Mumbai",
            origin_code="BOM",
            destination_city="Delhi",
            destination_code="DEL",
            departure_time=datetime(2026, 11, 14, 12, 0),
            arrival_time=datetime(2026, 11, 14, 14, 15),
            duration_minutes=135,
            stops=0,
            layover_duration_minutes=0,
            price_per_adult=5000.0,
            available_seats=15,
        ),
    ]

# Sample hotels fixtures
@pytest.fixture
def sample_hotels():
    return [
        HotelDTO(
            id=1,
            name="Budget Stay Colaba",
            city="Mumbai",
            star_rating=3,
            price_per_night=2500.0,
            amenities=["Free WiFi", "Air Conditioning"],
            available_rooms=5,
            max_occupancy_per_room=2,
        ),
        HotelDTO(
            id=2,
            name="Executive Grand Fort",
            city="Mumbai",
            star_rating=4,
            price_per_night=5500.0,
            amenities=["Free WiFi", "Swimming Pool", "Breakfast Included"],
            available_rooms=4,
            max_occupancy_per_room=2,
        ),
        HotelDTO(
            id=3,
            name="The Royal Palace Mumbai",
            city="Mumbai",
            star_rating=5,
            price_per_night=22000.0,
            amenities=["Free WiFi", "Swimming Pool", "Spa", "Ocean View"],
            available_rooms=2,
            max_occupancy_per_room=2,
        ),
    ]

class TestAgentLogic:
    def test_perception_validation_errors(self, sample_flights, sample_hotels):
        agent = ConciergeAgent()
        
        # Inverted dates
        req_bad_dates = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 15),
            return_date=date(2026, 11, 10),
            adults=1,
            budget=50000.0
        )
        res = agent.run(req_bad_dates, sample_flights, sample_hotels)
        assert res.status == "INVALID_INPUT"
        assert "precede departure date" in res.explanation

        # Identical cities
        req_same_cities = TravelRequirements(
            departure_city="Delhi",
            destination_city="Delhi",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=1,
            budget=50000.0
        )
        res = agent.run(req_same_cities, sample_flights, sample_hotels)
        assert res.status == "INVALID_INPUT"
        assert "cannot both be" in res.explanation

    def test_room_calculation(self):
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=3,
            budget=50000.0,
            room_sharing=True
        )
        hotel = HotelDTO(
            id=1, name="Test", city="Mumbai", star_rating=3,
            price_per_night=2000.0, amenities=[], available_rooms=5, max_occupancy_per_room=2
        )
        # 3 adults, max occupancy 2 -> 2 rooms
        assert calculate_rooms_required(req, hotel) == 2

        # without room sharing -> 3 rooms
        req.room_sharing = False
        assert calculate_rooms_required(req, hotel) == 3

    def test_tight_budget_optimization(self, sample_flights, sample_hotels):
        """Scenario 1: Find the cheapest valid package under tight budget."""
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),  # 4 nights
            adults=1,
            budget=20000.0,  # tight budget
            preferred_hotel_stars=3,
            hotel_category_is_hard=True
        )
        result = agent.run(req, sample_flights, sample_hotels)
        assert result.status == "SUCCESS"
        assert result.best_package is not None
        
        # Cheapest flight pair: SG-202 (3500) + 6E-102 (4200) = 7700
        # Hotel: 2500 * 4 nights = 10000
        # Total = 17700 <= 20000
        assert result.best_package.hotel.star_rating == 3
        assert result.best_package.total_cost == 17700.0
        assert result.best_package.remaining_budget == 2300.0
        assert "Optimal travel package" in result.message

    def test_luxury_trip_satisfaction(self, sample_flights, sample_hotels):
        """Scenario 2: Luxury trip with strict 5-star hotel and ample budget."""
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),  # 4 nights
            adults=2,
            budget=150000.0,  # luxury budget
            preferred_hotel_stars=5,
            hotel_category_is_hard=True
        )
        result = agent.run(req, sample_flights, sample_hotels)
        assert result.status == "SUCCESS"
        assert result.best_package is not None
        assert result.best_package.hotel.star_rating == 5
        assert result.best_package.hotel.name == "The Royal Palace Mumbai"

    def test_infeasible_budget_and_explanation(self, sample_flights, sample_hotels):
        """Scenario 3: Infeasible budget results in no package and clear actionable diagnosis."""
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=1,
            budget=5000.0,  # Impossible budget: cheapest flight alone is 7700
            preferred_hotel_stars=3
        )
        result = agent.run(req, sample_flights, sample_hotels)
        assert result.status == "NO_FEASIBLE_PACKAGE"
        assert result.best_package is None
        assert len(result.actionable_suggestions) > 0
        assert "budget" in result.explanation.lower()
        assert result.rejection_summary.budget_exceeded > 0

    def test_deterministic_tie_breaking(self):
        """Verify deterministic tie-breaking when two packages have identical total cost."""
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=1,
            budget=50000.0
        )
        
        hotel = HotelDTO(
            id=1, name="Hotel Alpha", city="Mumbai", star_rating=4,
            price_per_night=5000.0, amenities=[], available_rooms=5, max_occupancy_per_room=2
        )
        
        # Package 1: 0 stops flight, total cost 15000
        flight_direct_out = FlightDTO(
            id=10, flight_number="DIR-01", airline="AirDirect",
            origin_city="Delhi", origin_code="DEL", destination_city="Mumbai", destination_code="BOM",
            departure_time=datetime(2026, 11, 10, 10, 0), arrival_time=datetime(2026, 11, 10, 12, 0),
            duration_minutes=120, stops=0, layover_duration_minutes=0, price_per_adult=5000.0, available_seats=5
        )
        flight_ret = FlightDTO(
            id=11, flight_number="RET-01", airline="AirDirect",
            origin_city="Mumbai", origin_code="BOM", destination_city="Delhi", destination_code="DEL",
            departure_time=datetime(2026, 11, 14, 10, 0), arrival_time=datetime(2026, 11, 14, 12, 0),
            duration_minutes=120, stops=0, layover_duration_minutes=0, price_per_adult=5000.0, available_seats=5
        )

        # Package 2: 1 stop flight, same total cost 15000
        flight_stop_out = FlightDTO(
            id=12, flight_number="STP-01", airline="AirStop",
            origin_city="Delhi", origin_code="DEL", destination_city="Mumbai", destination_code="BOM",
            departure_time=datetime(2026, 11, 10, 10, 0), arrival_time=datetime(2026, 11, 10, 15, 0),
            duration_minutes=300, stops=1, layover_duration_minutes=60, price_per_adult=5000.0, available_seats=5
        )

        pkg_direct = TravelPackage(
            outbound_flight=flight_direct_out,
            return_flight=flight_ret,
            hotel=hotel,
            nights=4,
            rooms_required=1,
            flight_cost=10000.0,
            hotel_cost=5000.0,
            total_cost=15000.0,
            remaining_budget=35000.0
        )

        pkg_stop = TravelPackage(
            outbound_flight=flight_stop_out,
            return_flight=flight_ret,
            hotel=hotel,
            nights=4,
            rooms_required=1,
            flight_cost=10000.0,
            hotel_cost=5000.0,
            total_cost=15000.0,
            remaining_budget=35000.0
        )

        # When passed in reverse order [pkg_stop, pkg_direct], direct must win tie-breaker (fewer stops)
        sorted_pkgs = sort_and_optimize_packages([pkg_stop, pkg_direct], req)
        assert sorted_pkgs[0].outbound_flight.flight_number == "DIR-01"
        assert sorted_pkgs[0].outbound_flight.stops == 0

    def test_explanation_accuracy_with_stops_under_soft_preference(self):
        """
        Regression test: When flights with stops are selected under a soft stop preference,
        the explanation must not falsely claim 'Non-stop' under Hard Constraints.
        Instead, it accurately states the round-trip route and retains the soft preference note.
        """
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=2,
            budget=50000.0,
            preferred_hotel_stars=3,
            max_flight_stops=0,
            max_flight_stops_is_hard=False,
        )
        flight_out = FlightDTO(
            id=1, flight_number="SG-162", airline="SpiceJet",
            origin_city="Delhi", origin_code="DEL", destination_city="Mumbai", destination_code="BOM",
            departure_time=datetime(2026, 11, 10, 11, 0), arrival_time=datetime(2026, 11, 10, 15, 30),
            duration_minutes=270, stops=1, layover_duration_minutes=75, price_per_adult=3600.0, available_seats=10
        )
        flight_ret = FlightDTO(
            id=2, flight_number="SG-163", airline="SpiceJet",
            origin_city="Mumbai", origin_code="BOM", destination_city="Delhi", destination_code="DEL",
            departure_time=datetime(2026, 11, 14, 18, 0), arrival_time=datetime(2026, 11, 14, 22, 30),
            duration_minutes=270, stops=1, layover_duration_minutes=75, price_per_adult=3550.0, available_seats=10
        )
        hotel = HotelDTO(
            id=1, name="Treebo Trend", city="Mumbai", star_rating=3,
            price_per_night=2800.0, amenities=["Free WiFi"], available_rooms=5, max_occupancy_per_room=2
        )

        res = agent.run(req, [flight_out, flight_ret], [hotel])
        assert res.status == "SUCCESS"
        assert res.best_package is not None
        assert res.best_package.outbound_flight.stops == 1
        assert res.best_package.return_flight.stops == 1

        explanation = res.explanation
        assert "non-stop" not in explanation.lower()
        assert "Valid round-trip route between Delhi and Mumbai" in explanation
        assert "2 total stops" in explanation
        assert "Exceeds preferred max stops (0)" in explanation

    def test_explanation_accuracy_with_hard_non_stop_constraint(self, sample_flights, sample_hotels):
        """
        Verifies that when max_flight_stops=0 is enforced as a HARD constraint on a seeded route,
        the explanation explicitly states 'Direct non-stop round-trip' and does not state 'Valid round-trip route'.
        """
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=1,
            budget=50000.0,
            preferred_hotel_stars=3,
            max_flight_stops=0,
            max_flight_stops_is_hard=True,
        )
        res = agent.run(req, sample_flights, sample_hotels)
        assert res.status == "SUCCESS"
        assert res.best_package is not None
        assert res.best_package.outbound_flight.stops == 0
        assert res.best_package.return_flight.stops == 0

        explanation = res.explanation
        assert "Direct non-stop round-trip" in explanation
        assert "Valid round-trip route" not in explanation

    def test_infeasible_suggestions_no_redundant_hotel_tier_when_hard_3_star_requested(self, sample_flights, sample_hotels):
        """
        Regression test: When the request already specifies a hard 3-star hotel requirement,
        the actionable suggestions must not redundantly suggest selecting a 3-star or 4-star tier.
        """
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=1,
            budget=4000.0,  # Below flight and hotel minimums
            preferred_hotel_stars=3,
            hotel_category_is_hard=True,
        )
        result = agent.run(req, sample_flights, sample_hotels)
        assert result.status == "NO_FEASIBLE_PACKAGE"
        assert len(result.actionable_suggestions) > 0

        joined_suggestions = " ".join(result.actionable_suggestions)
        # Verify no redundant suggestion to select 3-star or 4-star
        assert "3★ or 4★" not in joined_suggestions
        assert "select a 3★" not in joined_suggestions
        assert "select a 4★" not in joined_suggestions
        # Verify appropriate constraint-based suggestions are provided
        assert "Flexible Hotel Category" in joined_suggestions
        assert "increasing your budget" in joined_suggestions

    def test_infeasible_suggestions_with_flexible_hotel_category_already_enabled(self, sample_flights, sample_hotels):
        """
        Regression test: When flexible hotel category was already enabled (hotel_category_is_hard=False),
        the suggestions should not redundantly ask the user to 'Enable Flexible Hotel Category'.
        """
        agent = ConciergeAgent()
        req = TravelRequirements(
            departure_city="Delhi",
            destination_city="Mumbai",
            departure_date=date(2026, 11, 10),
            return_date=date(2026, 11, 14),
            adults=1,
            budget=2000.0,
            preferred_hotel_stars=3,
            hotel_category_is_hard=False,
        )
        result = agent.run(req, sample_flights, sample_hotels)
        assert result.status == "NO_FEASIBLE_PACKAGE"
        assert len(result.actionable_suggestions) > 0

        joined_suggestions = " ".join(result.actionable_suggestions)
        assert "Enable 'Flexible Hotel Category'" not in joined_suggestions
