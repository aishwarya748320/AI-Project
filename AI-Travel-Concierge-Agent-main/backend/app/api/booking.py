from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import get_travel_provider
from app.schemas.booking import (
    VerifyOfferRequest,
    VerifyOfferResponse,
    BookingConfirmRequest,
    BookingConfirmResponse,
)

router = APIRouter(tags=["Booking & Verification"])

@router.post("/verify-offer", response_model=VerifyOfferResponse, status_code=status.HTTP_200_OK)
def verify_offer(
    payload: VerifyOfferRequest,
    db: Session = Depends(get_db)
):
    """
    Revalidates the selected offer's pricing and seat/room availability before booking.
    Never proceeds with stale or repriced inventory.
    """
    provider = get_travel_provider(db=db)
    pkg = dict(payload.package_details) if payload.package_details else {}
    if "currency" not in pkg:
        pkg["currency"] = payload.currency

    result = provider.verify_offer(
        offer_id=payload.offer_id,
        expected_price=payload.expected_price,
        package_details=pkg,
    )
    return VerifyOfferResponse(
        verified=result.get("verified", False),
        status=result.get("status", "UNKNOWN"),
        offer_id=payload.offer_id,
        data_source=result.get("data_source", provider.provider_name),
        currency=result.get("currency", payload.currency),
        current_price=result.get("current_price"),
        price_difference=result.get("price_difference"),
        message=result.get("message", "Verification completed."),
    )

@router.post("/booking/confirm", response_model=BookingConfirmResponse, status_code=status.HTTP_200_OK)
def confirm_booking(
    payload: BookingConfirmRequest,
    db: Session = Depends(get_db)
):
    """
    Submits a booking only when explicit traveler confirmation is granted.
    Under simulated mode, creates an educational tracked reservation and clearly labels it as simulated.
    """
    if not payload.confirm:
        return BookingConfirmResponse(
            success=False,
            status="CONFIRMATION_REQUIRED",
            booking_reference=None,
            data_source="SIMULATED",
            currency=payload.package_details.get("currency", "INR") if payload.package_details else "INR",
            total_charged=0.0,
            customer_name=payload.customer.name,
            disclaimer="No booking attempted. Explicit confirmation is required.",
            message="Booking submission rejected: explicit confirmation flag 'confirm' must be True.",
        )

    provider = get_travel_provider(db=db)
    pkg = dict(payload.package_details) if payload.package_details else {}
    if "offer_id" not in pkg:
        pkg["offer_id"] = payload.offer_id
    if "currency" not in pkg:
        pkg["currency"] = "INR"

    result = provider.book_package(
        package_details=pkg,
        customer_details=payload.customer.model_dump(),
        explicit_confirmation=payload.confirm,
    )

    return BookingConfirmResponse(
        success=result.get("success", False),
        status=result.get("status", "UNKNOWN"),
        booking_reference=result.get("booking_reference"),
        data_source=result.get("data_source", provider.provider_name),
        currency=result.get("currency", "INR"),
        total_charged=result.get("total_charged", 0.0),
        customer_name=result.get("customer_name", payload.customer.name),
        handoff_url=result.get("handoff_url"),
        disclaimer=result.get(
            "disclaimer",
            "This is a demonstration reservation. No live payment was processed."
        ),
        message=result.get("message", "Booking processed."),
    )
