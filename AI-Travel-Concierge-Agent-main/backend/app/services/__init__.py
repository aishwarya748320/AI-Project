from typing import Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.services.provider_interface import BaseTravelProvider
from app.services.simulated_provider import SimulatedTravelProvider

def get_travel_provider(
    mode: Optional[str] = None,
    db: Optional[Session] = None,
) -> BaseTravelProvider:
    """
    Factory function returning the configured travel inventory provider.
    Defaults to SimulatedTravelProvider for rock-solid deterministic academic demonstration.
    """
    selected_mode = (mode or getattr(settings, "PROVIDER_MODE", "simulated")).lower()

    if selected_mode == "amadeus":
        try:
            from app.services.amadeus_provider import AmadeusTravelProvider
            return AmadeusTravelProvider(db=db)
        except Exception as e:
            print(f"Notice: Amadeus provider unavailable ({e}). Falling back to simulated provider.")
            return SimulatedTravelProvider(db=db)

    return SimulatedTravelProvider(db=db)
