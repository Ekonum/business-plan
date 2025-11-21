from datetime import date
from typing import Dict, List, Optional

from pydantic import BaseModel


class MonthlyBreakdown(BaseModel):
    month: date
    revenue: float
    variable_costs: float
    fixed_costs: float
    amortization: float
    loan_interest: float
    loan_principal: float
    ebt: float
    cash: float


class ProjectionResponse(BaseModel):
    periods: List[MonthlyBreakdown]
    metadata: Dict[str, Optional[str]]
