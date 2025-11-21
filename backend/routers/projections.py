from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from backend.db import get_session
from backend.schemas.projection import ProjectionResponse
from backend.services.calculations import compute_projection

router = APIRouter(prefix="/api", tags=["projection"])


@router.get("/projections", response_model=ProjectionResponse)
def get_projection(
    start_year: int = Query(..., description="Fiscal year starting year (e.g. 2024 for 2024-2025)"),
    years: int = Query(3, ge=1, le=10, description="Number of fiscal years to project"),
    initial_cash: float = Query(0.0, description="Opening cash balance"),
    session: Session = Depends(get_session),
):
    periods = compute_projection(session, start_year=start_year, years=years, initial_cash=initial_cash)
    return ProjectionResponse(periods=periods, metadata={"start_year": str(start_year), "years": str(years)})
