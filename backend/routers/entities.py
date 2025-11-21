from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from backend.db import get_session
from backend.models import Asset, ActualEntry, Contract, FixedCost, Loan, Offer, PaymentEvent

router = APIRouter(prefix="/api", tags=["entities"])


@router.post("/offers", response_model=Offer)
def create_offer(offer: Offer, session: Session = Depends(get_session)):
    session.add(offer)
    session.commit()
    session.refresh(offer)
    return offer


@router.get("/offers", response_model=list[Offer])
def list_offers(session: Session = Depends(get_session)):
    return session.exec(select(Offer)).all()


@router.post("/contracts", response_model=Contract)
def create_contract(contract: Contract, session: Session = Depends(get_session)):
    session.add(contract)
    session.commit()
    session.refresh(contract)
    return contract


@router.get("/contracts", response_model=list[Contract])
def list_contracts(session: Session = Depends(get_session)):
    return session.exec(select(Contract)).all()


@router.post("/payments", response_model=PaymentEvent)
def create_payment(event: PaymentEvent, session: Session = Depends(get_session)):
    contract = session.get(Contract, event.contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


@router.get("/payments", response_model=list[PaymentEvent])
def list_payments(session: Session = Depends(get_session)):
    return session.exec(select(PaymentEvent)).all()


@router.post("/fixed-costs", response_model=FixedCost)
def create_fixed_cost(cost: FixedCost, session: Session = Depends(get_session)):
    session.add(cost)
    session.commit()
    session.refresh(cost)
    return cost


@router.get("/fixed-costs", response_model=list[FixedCost])
def list_fixed_costs(session: Session = Depends(get_session)):
    return session.exec(select(FixedCost)).all()


@router.post("/assets", response_model=Asset)
def create_asset(asset: Asset, session: Session = Depends(get_session)):
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


@router.get("/assets", response_model=list[Asset])
def list_assets(session: Session = Depends(get_session)):
    return session.exec(select(Asset)).all()


@router.post("/loans", response_model=Loan)
def create_loan(loan: Loan, session: Session = Depends(get_session)):
    session.add(loan)
    session.commit()
    session.refresh(loan)
    return loan


@router.get("/loans", response_model=list[Loan])
def list_loans(session: Session = Depends(get_session)):
    return session.exec(select(Loan)).all()


@router.post("/actuals", response_model=ActualEntry)
def create_actual(entry: ActualEntry, session: Session = Depends(get_session)):
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@router.get("/actuals", response_model=list[ActualEntry])
def list_actuals(session: Session = Depends(get_session)):
    return session.exec(select(ActualEntry)).all()
