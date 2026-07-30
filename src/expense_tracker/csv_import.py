from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from .models import Transaction, parse_amount_to_cents


def parse_bawag_csv(
    lines: Iterable[str],
    *,
    account_id: str | None = None,
) -> list[Transaction]:
    """Parse rows from a headerless BAWAG Umsatzliste CSV export."""
    transactions: list[Transaction] = []

    for line_number, row in enumerate(csv.reader(lines, delimiter=";"), start=1):
        if not row or all(not field.strip() for field in row):
            continue

        if len(row) != 6:
            raise ValueError(
                f"BAWAG CSV row {line_number} has {len(row)} fields; expected 6"
            )

        bank_account, narrative, booking_date, _value_date, amount, currency = (
            field.strip() for field in row
        )
        resolved_account_id = account_id or bank_account
        if not resolved_account_id:
            raise ValueError(f"BAWAG CSV row {line_number} has no account ID")
        if currency.upper() != "EUR":
            raise ValueError(
                f"BAWAG CSV row {line_number} uses unsupported currency {currency!r}"
            )

        merchant, city = parse_narrative(narrative)
        title = merchant or narrative.split("|", maxsplit=1)[0].strip()
        city = city if merchant else ""
        source_id = sha256(
            "\x1f".join(row).encode("utf-8")
        ).hexdigest()

        transactions.append(
            Transaction(
                id=f"{resolved_account_id}:{source_id}",
                account_id=resolved_account_id,
                source_id=source_id,
                booking_date=datetime.strptime(
                    booking_date,
                    "%d.%m.%Y",
                ).date(),
                amount_cents=parse_amount_to_cents(amount),
                title=title,
                city=city,
            )
        )

    return transactions


def load_bawag_csv(
    path: str | Path,
    *,
    account_id: str | None = None,
) -> list[Transaction]:
    """Load and parse a BAWAG Umsatzliste CSV export from disk."""
    with Path(path).open(encoding="cp1252", newline="") as csv_file:
        return parse_bawag_csv(csv_file, account_id=account_id)


def parse_narrative(raw: str) -> tuple[str, str]:
    """
    Parse this bank's card transaction narrative format.

    Segment 0: transaction type + card ref
    Segment 1: terminal/POS metadata, or "AUTOMAT ..." for cash withdrawals
    Segment 2: merchant\\city\\postal — present for POS/e-comm, absent for ATM
    Segment 3+ (if present): fee/exchange-rate info — ignored for now

    E-commerce narratives may contain a merchant code rather than a city in the
    second merchant-field component.
    """
    segments = [segment.strip() for segment in raw.split("|")]

    if len(segments) > 1 and segments[1].upper().startswith("AUTOMAT"):
        return "ATM Withdrawal", segments[1]

    if len(segments) < 3:
        return "", raw.strip()

    merchant_field = segments[2]
    parts = [part for part in merchant_field.split("\\") if part.strip()]
    merchant = parts[0] if parts else merchant_field
    city = parts[1] if len(parts) > 1 else ""

    return merchant, city
