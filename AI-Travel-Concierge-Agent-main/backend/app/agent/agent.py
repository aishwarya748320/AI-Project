from typing import List, Optional, Sequence
from datetime import date
from app.agent.types import (
    TravelRequirements,
    FlightDTO,
    HotelDTO,
    TravelPackage,
    AgentResult,
    RejectionSummary,
)
from app.agent.constraints import check_hard_constraints
from app.agent.optimizer import sort_and_optimize_packages
from app.agent.explainer import (
    generate_recommendation_explanation,
    generate_infeasible_explanation,
)

class ConciergeAgent:
    """
    Goal-Based Intelligent Agent for E-Commerce Travel Recommendations.
    Evaluates feasible travel packages across 7 stages:
      1. Perception & input validation
      2. Goal formulation
      3. Candidate generation & early pruning
      4. Constraint satisfaction
      5. Cost calculation
      6. Cost minimization with deterministic multi-criteria tie-breaking
      7. Explanation & diagnostic reporting
    """

    def __init__(self, goal_description: Optional[str] = None):
        self.goal = goal_description or (
            "Find the lowest-cost valid round-trip flight and hotel package satisfying every hard constraint."
        )

    def run(
        self,
        requirements: TravelRequirements,
        available_flights: Sequence[FlightDTO],
        available_hotels: Sequence[HotelDTO],
    ) -> AgentResult:
        # =====================================================================
        # STAGE 1: PERCEPTION & VALIDATION
        # =====================================================================
        validation_error = self._validate_perception(requirements)
        if validation_error:
            return AgentResult(
                status="INVALID_INPUT",
                message=validation_error,
                explanation=validation_error,
                actionable_suggestions=[
                    "Ensure return date is on or after departure date.",
                    "Departure and destination cities must be different.",
                    "Number of adult travelers and budget must be positive numbers.",
                    "Multi-city itineraries are not supported in round-trip mode."
                ]
            )

        # =====================================================================
        # STAGE 2: GOAL FORMULATION
        # =====================================================================
        # Primary objective: Minimize total_cost while hard_constraints(package) == True

        # =====================================================================
        # STAGE 3: CANDIDATE GENERATION & EARLY PRUNING
        # =====================================================================
        rejections = RejectionSummary()

        dep_city_lower = requirements.departure_city.strip().lower()
        dest_city_lower = requirements.destination_city.strip().lower()

        # Filter outbound flights
        candidate_outbounds: List[FlightDTO] = []
        for f in available_flights:
            if f.origin_city.strip().lower() == dep_city_lower and f.destination_city.strip().lower() == dest_city_lower:
                if f.departure_time.date() == requirements.departure_date:
                    if f.available_seats >= requirements.adults:
                        candidate_outbounds.append(f)
                    else:
                        rejections.insufficient_flight_seats += 1
                else:
                    rejections.date_incompatible += 1
            else:
                rejections.route_incompatible += 1

        # Filter return flights
        candidate_returns: List[FlightDTO] = []
        for f in available_flights:
            if f.origin_city.strip().lower() == dest_city_lower and f.destination_city.strip().lower() == dep_city_lower:
                if f.departure_time.date() == requirements.return_date:
                    if f.available_seats >= requirements.adults:
                        candidate_returns.append(f)
                    else:
                        rejections.insufficient_flight_seats += 1
                else:
                    rejections.date_incompatible += 1
            else:
                rejections.route_incompatible += 1

        # Filter destination hotels
        candidate_hotels: List[HotelDTO] = [
            h for h in available_hotels if h.city.strip().lower() == dest_city_lower
        ]

        if not candidate_outbounds or not candidate_returns or not candidate_hotels:
            explanation, suggestions = generate_infeasible_explanation(requirements, rejections)
            return AgentResult(
                status="NO_FEASIBLE_PACKAGE",
                message="No compatible flights or hotels found for the requested route and dates.",
                explanation=explanation,
                actionable_suggestions=suggestions,
                rejection_summary=rejections
            )

        # =====================================================================
        # STAGE 4 & 5: CONSTRAINT SATISFACTION & COST CALCULATION
        # =====================================================================
        valid_packages, rejections = self._evaluate_candidates(
            requirements, candidate_outbounds, candidate_returns, candidate_hotels, allow_star_relaxation=False
        )

        # If no valid packages found and hotel category was marked flexible, try relaxing star rating by +/- 1
        if not valid_packages and not requirements.hotel_category_is_hard and requirements.preferred_hotel_stars is not None:
            valid_packages, rejections = self._evaluate_candidates(
                requirements, candidate_outbounds, candidate_returns, candidate_hotels, allow_star_relaxation=True
            )

        if not valid_packages:
            explanation, suggestions = generate_infeasible_explanation(requirements, rejections)
            return AgentResult(
                status="NO_FEASIBLE_PACKAGE",
                message="No package satisfied all hard constraints and budget.",
                explanation=explanation,
                actionable_suggestions=suggestions,
                rejection_summary=rejections
            )

        # =====================================================================
        # STAGE 6: OPTIMIZATION & DETERMINISTIC TIE-BREAKING
        # =====================================================================
        optimized_packages = sort_and_optimize_packages(valid_packages, requirements)

        best_package = optimized_packages[0]
        # Return 2 to 3 valid alternatives ranked by cost
        alternatives = optimized_packages[1:4]

        # =====================================================================
        # STAGE 7: EXPLANATION
        # =====================================================================
        explanation = generate_recommendation_explanation(
            best_package,
            requirements,
            alternative_count=len(alternatives),
            rejections=rejections
        )

        return AgentResult(
            status="SUCCESS",
            message="Optimal travel package identified satisfying all hard constraints.",
            data_source=best_package.data_source,
            currency=best_package.currency,
            best_package=best_package,
            alternative_packages=alternatives,
            explanation=explanation,
            itemized_cost_breakdown=best_package.itemized_cost_breakdown,
            assumptions=best_package.assumptions,
            actionable_suggestions=[],
            rejection_summary=rejections
        )

    def _validate_perception(self, req: TravelRequirements) -> Optional[str]:
        """Validates travel requirements before goal execution."""
        if req.departure_city.strip().lower() == req.destination_city.strip().lower():
            return f"Departure city and destination city cannot both be '{req.departure_city}'."
        if req.return_date < req.departure_date:
            return f"Return date ({req.return_date}) cannot precede departure date ({req.departure_date})."
        if req.adults <= 0:
            return "Number of adult travelers must be greater than zero."
        if req.budget <= 0:
            return "Total budget must be a positive number."
        return None

    def _evaluate_candidates(
        self,
        req: TravelRequirements,
        outbounds: List[FlightDTO],
        returns: List[FlightDTO],
        hotels: List[HotelDTO],
        allow_star_relaxation: bool
    ) -> tuple[List[TravelPackage], RejectionSummary]:
        rejections = RejectionSummary()
        valid_packages: List[TravelPackage] = []

        for out_flight in outbounds:
            for ret_flight in returns:
                for hotel in hotels:
                    rejections.total_combinations_evaluated += 1

                    is_valid, violations, rooms_req, flight_cost, hotel_cost, total_cost = check_hard_constraints(
                        req, out_flight, ret_flight, hotel, allow_star_relaxation=allow_star_relaxation
                    )

                    if not is_valid:
                        # Record metrics for diagnosis
                        for v in violations:
                            if v.constraint_name == "budget_exceeded":
                                rejections.budget_exceeded += 1
                            elif "hotel_star_rating" in v.constraint_name:
                                rejections.hotel_stars_mismatch += 1
                            elif "capacity" in v.constraint_name:
                                rejections.insufficient_hotel_rooms += 1
                            elif "flight_stops" in v.constraint_name:
                                rejections.stops_exceeded += 1
                            elif "amenities" in v.constraint_name:
                                rejections.amenities_missing += 1
                        continue

                    assumptions = [
                        f"Quoted airfares are per passenger (₹{out_flight.price_per_adult:,.0f} outbound + ₹{ret_flight.price_per_adult:,.0f} return), inclusive of taxes.",
                        f"Hotel rate of ₹{hotel.price_per_night:,.0f}/night calculated for {rooms_req} room(s) across {req.nights} night(s).",
                        ("Standard occupancy: 2 adults per room under room-sharing preference." if req.room_sharing else f"Individual private room allocated per adult traveler ({req.adults} rooms).")
                    ]
                    breakdown = {
                        "currency": "INR",
                        "adults": req.adults,
                        "nights": req.nights,
                        "rooms_required": rooms_req,
                        "outbound_fare_per_adult": out_flight.price_per_adult,
                        "return_fare_per_adult": ret_flight.price_per_adult,
                        "total_flight_cost": flight_cost,
                        "hotel_nightly_rate": hotel.price_per_night,
                        "total_hotel_cost": hotel_cost,
                        "total_package_cost": total_cost,
                        "budget": req.budget,
                        "remaining_budget": req.budget - total_cost,
                    }

                    pkg = TravelPackage(
                        package_id=f"PKG-{out_flight.flight_number}-{ret_flight.flight_number}-{hotel.id}",
                        data_source=out_flight.data_source,
                        currency="INR",
                        outbound_flight=out_flight,
                        return_flight=ret_flight,
                        hotel=hotel,
                        nights=req.nights,
                        rooms_required=rooms_req,
                        flight_cost=flight_cost,
                        hotel_cost=hotel_cost,
                        total_cost=total_cost,
                        remaining_budget=req.budget - total_cost,
                        itemized_cost_breakdown=breakdown,
                        assumptions=assumptions,
                        is_relaxed_hotel_category=allow_star_relaxation and (hotel.star_rating != req.preferred_hotel_stars)
                    )
                    valid_packages.append(pkg)

        return valid_packages, rejections
