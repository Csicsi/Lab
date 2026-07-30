from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class Account(BaseModel):
    id: str
    name: str
    currency: str = "EUR"


class Category(BaseModel):
    id: str
    name: str
    is_income: bool = False


class Transaction(BaseModel):
    id: str
    account_id: str
    source_id: str
    booking_date: date
    amount_cents: int
    title: str = ""
    city: str = ""
    raw_description: str = ""
    source_record: str = ""
    category_id: str | None = None

    @property
    def is_expense(self) -> bool:
        return self.amount_cents < 0

    @property
    def is_income(self) -> bool:
        return self.amount_cents >= 0


def parse_amount_to_cents(raw: str) -> int:
    deseparated = raw.strip().replace(".", "")
    normalized = deseparated.replace(",", ".")
    return int((Decimal(normalized) * 100).to_integral_value())
