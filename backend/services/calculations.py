from datetime import date
from math import pow
from typing import Dict, Iterable, List, Tuple

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from backend.models import (
    Asset,
    ActualCategory,
    ActualEntry,
    Contract,
    FixedCost,
    Loan,
    Offer,
    OfferType,
    PaymentEvent,
    Recurrence,
)
from backend.schemas.projection import BudgetVsActualRow, MonthlyBreakdown


FISCAL_START_MONTH = 10


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def generate_months(start_year: int, years: int, fiscal_start_month: int = FISCAL_START_MONTH) -> List[date]:
    start = date(start_year, fiscal_start_month, 1)
    return [start + relativedelta(months=i) for i in range(years * 12)]


def _ensure_offer_map(session: Session) -> Dict[int, Offer]:
    offers = session.exec(select(Offer)).all()
    return {offer.id: offer for offer in offers}


def _collect_payment_plan(
    session: Session, contract: Contract, months: Iterable[date], offer: Offer
) -> List[Tuple[date, float]]:
    # If explicit payment events exist, use them.
    if contract.id:
        explicit_events = session_payment_events(session, contract, months)
        if explicit_events:
            return explicit_events

    # Build synthetic payment plan based on recurrence.
    plan: List[Tuple[date, float]] = []
    if contract.recurrence == Recurrence.ONE_TIME:
        plan.append((month_start(contract.start_date), contract.total_value * contract.quantity))
    elif contract.recurrence == Recurrence.MONTHLY:
        for m in months:
            if m >= month_start(contract.start_date) and (not contract.end_date or m <= month_start(contract.end_date)):
                plan.append((m, contract.total_value * contract.quantity))
    elif contract.recurrence == Recurrence.ANNUAL:
        for m in months:
            if m.month == contract.start_date.month and m >= month_start(contract.start_date):
                if not contract.end_date or m <= month_start(contract.end_date):
                    plan.append((m, contract.total_value * contract.quantity))
    return plan

def session_payment_events(
    session: Session, contract: Contract, months: Iterable[date]
) -> List[Tuple[date, float]]:
    events: List[Tuple[date, float]] = []
    if not contract.id:
        return events
    for evt in session.exec(select(PaymentEvent).where(PaymentEvent.contract_id == contract.id)).all():
        due_month = month_start(evt.due_date)
        if due_month in months:
            events.append((due_month, evt.amount))
    return events


def compute_projection(session: Session, start_year: int, years: int, initial_cash: float = 0.0) -> List[MonthlyBreakdown]:
    months = generate_months(start_year, years)
    offer_map = _ensure_offer_map(session)

    revenue: Dict[date, float] = {m: 0.0 for m in months}
    variable_costs: Dict[date, float] = {m: 0.0 for m in months}
    cash_inflows: Dict[date, float] = {m: 0.0 for m in months}
    cash_outflows: Dict[date, float] = {m: 0.0 for m in months}
    fixed_costs: Dict[date, float] = {m: 0.0 for m in months}

    # Contracts and payments
    for contract in session.exec(select(Contract)).all():
        offer = offer_map.get(contract.offer_id)
        if not offer:
            continue
        plan = _collect_payment_plan(session, contract, months, offer)
        for due_month, amount in plan:
            if due_month in revenue:
                revenue[due_month] += amount
                if offer.offer_type == OfferType.LICENSE:
                    variable_costs[due_month] += amount * (offer.variable_cost_rate or 0.88)
                elif offer.variable_cost_rate:
                    variable_costs[due_month] += amount * offer.variable_cost_rate
            if due_month in cash_inflows:
                cash_inflows[due_month] += amount * (1 + contract.tax_rate)

    # Fixed costs
    for fixed in session.exec(select(FixedCost)).all():
        for m in months:
            if m >= month_start(fixed.start_date) and (not fixed.end_date or m <= month_start(fixed.end_date)):
                fixed_costs[m] += fixed.monthly_amount
                cash_outflows[m] += fixed.monthly_amount

    # Assets amortization
    amortization: Dict[date, float] = {m: 0.0 for m in months}
    for asset in session.exec(select(Asset)).all():
        monthly = asset.purchase_amount / asset.amortization_months
        for i in range(asset.amortization_months):
            m = month_start(asset.purchase_date) + relativedelta(months=i)
            if m in amortization:
                amortization[m] += monthly
                cash_outflows[m] += 0 if i else asset.purchase_amount  # purchase at start

    # Loans schedule (annuity)
    loan_interest: Dict[date, float] = {m: 0.0 for m in months}
    loan_principal: Dict[date, float] = {m: 0.0 for m in months}
    for loan in session.exec(select(Loan)).all():
        monthly_rate = loan.annual_rate / 12
        payment = loan.principal * (monthly_rate / (1 - pow(1 + monthly_rate, -loan.term_months)))
        balance = loan.principal
        for i in range(loan.term_months):
            m = month_start(loan.start_date) + relativedelta(months=i)
            if m not in loan_interest:
                continue
            interest = balance * monthly_rate
            principal = payment - interest
            balance -= principal
            loan_interest[m] += interest
            loan_principal[m] += principal
            cash_outflows[m] += payment

    # Build monthly breakdown
    breakdown: List[MonthlyBreakdown] = []
    cumulative_cash = initial_cash
    for m in months:
        pnl_revenue = revenue[m]
        pnl_variable = variable_costs[m]
        pnl_fixed = fixed_costs[m]
        pnl_amort = amortization[m]
        pnl_interest = loan_interest[m]
        pnl_principal = loan_principal[m]
        ebt = pnl_revenue - pnl_variable - pnl_fixed - pnl_amort - pnl_interest
        net_cash_flow = cash_inflows[m] - cash_outflows[m]
        cumulative_cash += net_cash_flow
        breakdown.append(
            MonthlyBreakdown(
                month=m,
                revenue=round(pnl_revenue, 2),
                variable_costs=round(pnl_variable, 2),
                fixed_costs=round(pnl_fixed, 2),
                amortization=round(pnl_amort, 2),
                loan_interest=round(pnl_interest, 2),
                loan_principal=round(pnl_principal, 2),
                ebt=round(ebt, 2),
                cash=round(cumulative_cash, 2),
            )
        )
    return breakdown


def aggregate_actuals(session: Session) -> Dict[date, Dict[ActualCategory, float]]:
    actuals: Dict[date, Dict[ActualCategory, float]] = {}
    for entry in session.exec(select(ActualEntry)).all():
        m = month_start(entry.entry_date)
        if m not in actuals:
            actuals[m] = {c: 0.0 for c in ActualCategory}
        actuals[m][entry.category] += entry.amount
    return actuals


def compute_budget_vs_actual(
    session: Session, start_year: int, years: int, initial_cash: float = 0.0
) -> List[BudgetVsActualRow]:
    budget = compute_projection(session, start_year=start_year, years=years, initial_cash=initial_cash)
    actuals = aggregate_actuals(session)

    rows: List[BudgetVsActualRow] = []
    actual_cash = initial_cash
    budget_by_month = {b.month: b for b in budget}

    for month in [b.month for b in budget]:
        month_actuals = actuals.get(month, {c: 0.0 for c in ActualCategory})
        actual_revenue = month_actuals[ActualCategory.REVENUE]
        actual_variable = month_actuals[ActualCategory.VARIABLE_COSTS]
        actual_fixed = month_actuals[ActualCategory.FIXED_COSTS]
        actual_amort = month_actuals[ActualCategory.AMORTIZATION]
        actual_interest = month_actuals[ActualCategory.LOAN_INTEREST]
        actual_principal = month_actuals[ActualCategory.LOAN_PRINCIPAL]
        actual_ebt = actual_revenue - actual_variable - actual_fixed - actual_amort - actual_interest
        actual_cash_flow = (
            actual_revenue
            - actual_variable
            - actual_fixed
            - actual_amort
            - actual_interest
            - actual_principal
        )
        actual_cash += actual_cash_flow

        budget_month = budget_by_month[month]

        budget_revenue = budget_month.revenue
        budget_variable = budget_month.variable_costs
        budget_fixed = budget_month.fixed_costs
        budget_amort = budget_month.amortization
        budget_interest = budget_month.loan_interest
        budget_principal = budget_month.loan_principal
        budget_ebt = budget_month.ebt
        budget_cash = budget_month.cash

        rows.append(
            BudgetVsActualRow(
                month=month,
                budget_revenue=budget_revenue,
                actual_revenue=round(actual_revenue, 2),
                variance_revenue=round(actual_revenue - budget_revenue, 2),
                budget_variable=budget_variable,
                actual_variable=round(actual_variable, 2),
                variance_variable=round(actual_variable - budget_variable, 2),
                budget_fixed=budget_fixed,
                actual_fixed=round(actual_fixed, 2),
                variance_fixed=round(actual_fixed - budget_fixed, 2),
                budget_amortization=budget_amort,
                actual_amortization=round(actual_amort, 2),
                variance_amortization=round(actual_amort - budget_amort, 2),
                budget_interest=budget_interest,
                actual_interest=round(actual_interest, 2),
                variance_interest=round(actual_interest - budget_interest, 2),
                budget_principal=budget_principal,
                actual_principal=round(actual_principal, 2),
                variance_principal=round(actual_principal - budget_principal, 2),
                budget_ebt=budget_ebt,
                actual_ebt=round(actual_ebt, 2),
                variance_ebt=round(actual_ebt - budget_ebt, 2),
                budget_cash=budget_cash,
                actual_cash=round(actual_cash, 2),
                variance_cash=round(actual_cash - budget_cash, 2),
            )
        )

    return rows
