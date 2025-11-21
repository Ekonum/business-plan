from datetime import date
from enum import Enum
from typing import Optional

from sqlmodel import Column, Date, Enum as SqlEnum, Field, SQLModel


class OfferType(str, Enum):
    ONE_OFF = "one_off"
    RECURRING = "recurring"
    LICENSE = "license"
    HARDWARE = "hardware"


class Recurrence(str, Enum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"
    ANNUAL = "annual"


class Offer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    offer_type: OfferType = Field(sa_column=Column(SqlEnum(OfferType)))
    default_price: float
    variable_cost_rate: Optional[float] = Field(
        default=None, description="Variable cost as % of revenue (e.g. 0.88 for 88%)"
    )


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_name: str
    offer_id: int = Field(foreign_key="offer.id")
    start_date: date
    end_date: Optional[date] = None
    recurrence: Recurrence = Field(default=Recurrence.ONE_TIME, sa_column=Column(SqlEnum(Recurrence)))
    total_value: float = Field(description="Total contract amount (excl. taxes)")
    quantity: int = Field(default=1)
    tax_rate: float = Field(default=0.2, description="VAT rate applied to payments")


class PaymentEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    contract_id: int = Field(foreign_key="contract.id")
    label: str
    due_date: date
    amount: float


class FixedCost(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    monthly_amount: float
    start_date: date
    end_date: Optional[date] = None


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    purchase_date: date
    purchase_amount: float
    amortization_months: int


class Loan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    principal: float
    annual_rate: float
    start_date: date
    term_months: int


class ActualEntry(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    entry_date: date = Field(sa_column=Column(Date))
    category: str
    amount: float
