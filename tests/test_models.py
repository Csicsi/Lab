from datetime import date

import pytest
from pydantic import ValidationError

from expense_tracker import (
    Account,
    Category,
    Transaction,
    parse_amount_to_cents,
    parse_narrative,
)


def test_account_uses_default_values() -> None:
    account = Account(
        id="bawag-main",
        name="BAWAG",
    )

    assert account.currency == "EUR"


def test_account_accepts_explicit_type() -> None:
    account = Account(
        id="savings-1",
        name="Savings account",
        currency="USD",
    )

    assert account.currency == "USD"


def test_category_is_expense_by_default() -> None:
    category = Category(
        id="groceries",
        name="Groceries",
    )

    assert category.is_income is False


def test_negative_transaction_is_expense() -> None:
    transaction = Transaction(
        id="bawag-main:123",
        account_id="bawag-main",
        source_id="123",
        booking_date=date(2026, 7, 29),
        amount_cents=-1549,
        title="BILLA",
    )

    assert transaction.is_expense is True
    assert transaction.is_income is False


def test_positive_transaction_is_income() -> None:
    transaction = Transaction(
        id="bawag-main:124",
        account_id="bawag-main",
        source_id="124",
        booking_date=date(2026, 7, 29),
        amount_cents=250_000,
        title="Salary",
    )

    assert transaction.is_income is True
    assert transaction.is_expense is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12,34", 1234),
        ("-12,34", -1234),
        (" 12,34 ", 1234),
        ("0,01", 1),
        ("100", 10_000),
        ("-1.234,56", -123_456),
    ],
)
def test_parse_amount_to_cents(raw: str, expected: int) -> None:
    assert parse_amount_to_cents(raw) == expected


def test_parse_narrative_extracts_merchant_and_city() -> None:
    raw = r"KARTENZAHLUNG 1234 | POS 5678 | BILLA\WIEN\1010"

    assert parse_narrative(raw) == ("BILLA", "WIEN")


def test_parse_narrative_recognizes_atm_withdrawal() -> None:
    raw = "BARGELDBEZUG 1234 | Automat Wien Hauptbahnhof"

    assert parse_narrative(raw) == (
        "ATM Withdrawal",
        "Automat Wien Hauptbahnhof",
    )


def test_parse_narrative_ignores_fee_information() -> None:
    raw = r"KARTENZAHLUNG 1234 | POS 5678 | SHOP\GRAZ\8010 | SPESEN: 1,50"

    assert parse_narrative(raw) == ("SHOP", "GRAZ")


@pytest.mark.parametrize("raw", ["", "KARTENZAHLUNG 1234"])
def test_parse_narrative_returns_raw_text_when_segments_are_missing(
    raw: str,
) -> None:
    assert parse_narrative(raw) == ("", raw.strip())
