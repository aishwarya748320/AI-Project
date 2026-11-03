from typing import List, Tuple
from app.agent.types import TravelPackage, TravelRequirements

def calculate_time_inconvenience(package: TravelPackage) -> float:
    """
    Computes a deterministic departure/arrival time convenience penalty.
    Target ideal departure hour is 10:00 AM (600 minutes from midnight).
    Penalizes departures before 06:00 or after 22:00.
    """
    out_hour = package.outbound_flight.departure_time.hour + package.outbound_flight.departure_time.minute / 60.0
    ret_hour = package.return_flight.departure_time.hour + package.return_flight.departure_time.minute / 60.0
    
    # Distance from comfortable mid-morning window (09:00 - 11:00)
    out_diff = abs(out_hour - 10.0)
    ret_diff = abs(ret_hour - 10.0)
    
    # Extra penalty for red-eye flights (before 06:00 or after 23:00)
    redeye = 0.0
    if out_hour < 6.0 or out_hour > 23.0:
        redeye += 20.0
    if ret_hour < 6.0 or ret_hour > 23.0:
        redeye += 20.0

    return out_diff + ret_diff + redeye


def evaluate_soft_constraints(package: TravelPackage, req: TravelRequirements) -> None:
    """
    Evaluates soft preferences and populates soft_penalties and convenience_score
    WITHOUT affecting the primary cost optimization.
    """
    penalties = []
    
    # Preferred airline
    if req.preferred_airline:
        pref = req.preferred_airline.lower()
        if package.outbound_flight.airline.lower() != pref or package.return_flight.airline.lower() != pref:
            penalties.append(f"Differs from preferred airline '{req.preferred_airline}'")
    
    # Soft flight stops
    if req.max_flight_stops is not None and not req.max_flight_stops_is_hard:
        total_stops = package.outbound_flight.stops + package.return_flight.stops
        if total_stops > req.max_flight_stops:
            penalties.append(f"Exceeds preferred max stops ({req.max_flight_stops})")

    # Soft amenities
    if req.preferred_amenities and not req.amenities_are_hard:
        hotel_amenities_lower = [a.lower() for a in package.hotel.amenities]
        missing = [a for a in req.preferred_amenities if a.lower() not in hotel_amenities_lower]
        if missing:
            penalties.append(f"Hotel lacks preferred amenities: {', '.join(missing)}")

    # Layover duration
    if req.max_layover_minutes is not None:
        if (package.outbound_flight.layover_duration_minutes > req.max_layover_minutes or 
            package.return_flight.layover_duration_minutes > req.max_layover_minutes):
            penalties.append(f"Layover exceeds preferred {req.max_layover_minutes} mins")

    package.soft_penalties = penalties
    package.convenience_score = calculate_time_inconvenience(package)


def sort_and_optimize_packages(
    packages: List[TravelPackage],
    req: TravelRequirements
) -> List[TravelPackage]:
    """
    Orders candidate packages strictly by the optimization specification:
    Primary Goal: Minimize total package cost.
    Deterministic Tie-Breakers (when costs are equal):
      1. Fewer flight stops (outbound + return)
      2. Shorter total travel duration (outbound + return)
      3. More convenient departure/arrival times (lower inconvenience score)
      4. Higher hotel rating
      5. Stable identifier tie-breaker
    """
    for pkg in packages:
        evaluate_soft_constraints(pkg, req)

    def package_sort_key(pkg: TravelPackage) -> Tuple:
        total_stops = pkg.outbound_flight.stops + pkg.return_flight.stops
        total_duration = pkg.outbound_flight.duration_minutes + pkg.return_flight.duration_minutes
        inconvenience = pkg.convenience_score
        neg_hotel_rating = -pkg.hotel.star_rating
        
        # Tie-breaker 5: Unique string for deterministic stability
        unique_key = f"{pkg.outbound_flight.flight_number}_{pkg.return_flight.flight_number}_{pkg.hotel.id}"

        return (
            round(pkg.total_cost, 2),  # Primary: Minimum total package cost
            total_stops,               # Tie-breaker 1: Fewer stops
            total_duration,            # Tie-breaker 2: Shorter duration
            round(inconvenience, 2),   # Tie-breaker 3: More convenient times
            neg_hotel_rating,          # Tie-breaker 4: Higher star rating
            unique_key                 # Deterministic fallback
        )

    return sorted(packages, key=package_sort_key)
