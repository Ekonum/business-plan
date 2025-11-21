from datetime import date
from math import pow
from typing import Dict, Iterable, List, Tuple

from dateutil.relativedelta import relativedelta
from sqlmodel import Session, select

from backend.models import Asset, Contract, FixedCost, Loan, Offer, OfferType, PaymentEvent, Recurrence
from backend.schemas.projection import MonthlyBreakdown


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
