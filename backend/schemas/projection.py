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


class BudgetVsActualRow(BaseModel):
    month: date
    budget_revenue: float
    actual_revenue: float
    variance_revenue: float
    budget_variable: float
    actual_variable: float
    variance_variable: float
    budget_fixed: float
    actual_fixed: float
    variance_fixed: float
    budget_amortization: float
    actual_amortization: float
    variance_amortization: float
    budget_interest: float
    actual_interest: float
    variance_interest: float
    budget_principal: float
    actual_principal: float
    variance_principal: float
    budget_ebt: float
    actual_ebt: float
    variance_ebt: float
    budget_cash: float
    actual_cash: float
    variance_cash: float


class BudgetVsActualResponse(BaseModel):
    rows: List[BudgetVsActualRow]
    metadata: Dict[str, Optional[str]]
