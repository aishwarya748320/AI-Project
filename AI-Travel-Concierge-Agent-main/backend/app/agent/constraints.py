import math
from typing import Tuple, List, Optional
from datetime import date
from app.agent.types import TravelRequirements, FlightDTO, HotelDTO, ConstraintViolation

def calculate_rooms_required(req: TravelRequirements, hotel: HotelDTO) -> int:
    """Calculates number of rooms needed based on party size, room-sharing, and occupancy."""
    if req.rooms_per_party is not None and req.rooms_per_party > 0:
        return req.rooms_per_party
    if not req.room_sharing:
        return req.adults
    return math.ceil(req.adults / max(1, hotel.max_occupancy_per_room))


def check_hard_constraints(
    req: TravelRequirements,
    outbound: FlightDTO,
    inbound: FlightDTO,
    hotel: HotelDTO,
    allow_star_relaxation: bool = False
) -> Tuple[bool, List[ConstraintViolation], int, float, float, float]:
    """
    Evaluates all Stage 4 hard constraints for a flight + hotel combination.
    Returns: (is_valid, violations, rooms_required, flight_cost, hotel_cost, total_cost)
    """
    violations: List[ConstraintViolation] = []

    # 1. Route continuity & cities
    if outbound.origin_city.lower() != req.departure_city.lower():
        violations.append(ConstraintViolation(
            constraint_name="outbound_origin",
            reason=f"Outbound origin '{outbound.origin_city}' does not match '{req.departure_city}'"
        ))
    if outbound.destination_city.lower() != req.destination_city.lower():
        violations.append(ConstraintViolation(
            constraint_name="outbound_destination",
            reason=f"Outbound destination '{outbound.destination_city}' does not match '{req.destination_city}'"
        ))
    if inbound.origin_city.lower() != req.destination_city.lower():
        violations.append(ConstraintViolation(
            constraint_name="return_origin",
            reason=f"Return flight origin '{inbound.origin_city}' does not match '{req.destination_city}'"
        ))
    if inbound.destination_city.lower() != req.departure_city.lower():
        violations.append(ConstraintViolation(
            constraint_name="return_destination",
            reason=f"Return flight destination '{inbound.destination_city}' does not match '{req.departure_city}'"
        ))
    if hotel.city.lower() != req.destination_city.lower():
        violations.append(ConstraintViolation(
            constraint_name="hotel_city",
            reason=f"Hotel '{hotel.name}' is in '{hotel.city}', but destination is '{req.destination_city}'"
        ))

    # 2. Date feasibility
    if outbound.departure_time.date() != req.departure_date:
        violations.append(ConstraintViolation(
            constraint_name="outbound_date",
            reason=f"Outbound flight date {outbound.departure_time.date()} does not match {req.departure_date}"
        ))
    if inbound.departure_time.date() != req.return_date:
        violations.append(ConstraintViolation(
            constraint_name="return_date",
            reason=f"Return flight date {inbound.departure_time.date()} does not match {req.return_date}"
        ))
    if inbound.departure_time <= outbound.arrival_time:
        violations.append(ConstraintViolation(
            constraint_name="temporal_order",
            reason="Return flight departs before or at outbound flight arrival time"
        ))

    # 3. Capacity checks
    if outbound.available_seats < req.adults:
        violations.append(ConstraintViolation(
            constraint_name="flight_capacity_outbound",
            reason=f"Outbound flight seats ({outbound.available_seats}) < required ({req.adults})"
        ))
    if inbound.available_seats < req.adults:
        violations.append(ConstraintViolation(
            constraint_name="flight_capacity_return",
            reason=f"Return flight seats ({inbound.available_seats}) < required ({req.adults})"
        ))

    rooms_required = calculate_rooms_required(req, hotel)
    if hotel.available_rooms < rooms_required:
        violations.append(ConstraintViolation(
            constraint_name="hotel_room_capacity",
            reason=f"Hotel rooms available ({hotel.available_rooms}) < required ({rooms_required})"
        ))

    # 4. Hotel category constraint
    if req.preferred_hotel_stars is not None:
        if not allow_star_relaxation:
            if hotel.star_rating != req.preferred_hotel_stars:
                violations.append(ConstraintViolation(
                    constraint_name="hotel_star_rating",
                    reason=f"Hotel rating {hotel.star_rating}★ does not match preferred {req.preferred_hotel_stars}★"
                ))
        else:
            if abs(hotel.star_rating - req.preferred_hotel_stars) > 1:
                violations.append(ConstraintViolation(
                    constraint_name="hotel_star_rating_relaxed",
                    reason=f"Hotel rating {hotel.star_rating}★ is outside relaxed range for {req.preferred_hotel_stars}★"
                ))

    # 5. Optional flight stops constraint (if marked hard)
    if req.max_flight_stops is not None and req.max_flight_stops_is_hard:
        if outbound.stops > req.max_flight_stops or inbound.stops > req.max_flight_stops:
            violations.append(ConstraintViolation(
                constraint_name="flight_stops_hard",
                reason=f"Flight stops exceed mandatory maximum of {req.max_flight_stops}"
            ))

    # 6. Optional hotel amenities constraint (if marked hard)
    if req.preferred_amenities and req.amenities_are_hard:
        hotel_amenities_lower = [a.lower() for a in hotel.amenities]
        missing = [a for a in req.preferred_amenities if a.lower() not in hotel_amenities_lower]
        if missing:
            violations.append(ConstraintViolation(
                constraint_name="hotel_amenities_hard",
                reason=f"Missing mandatory amenities: {', '.join(missing)}"
            ))

    # 7. Cost calculation and budget check
    nights = req.nights
    flight_cost = (outbound.price_per_adult + inbound.price_per_adult) * req.adults
    hotel_cost = hotel.price_per_night * nights * rooms_required
    total_cost = flight_cost + hotel_cost

    if total_cost > req.budget:
        violations.append(ConstraintViolation(
            constraint_name="budget_exceeded",
            reason=f"Total cost ₹{total_cost:,.2f} exceeds budget ₹{req.budget:,.2f} by ₹{(total_cost - req.budget):,.2f}"
        ))

    is_valid = len(violations) == 0
    return is_valid, violations, rooms_required, flight_cost, hotel_cost, total_cost
