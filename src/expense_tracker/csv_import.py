from __future__ import annotations

import csv
from collections.abc import Iterable
from datetime import datetime
from hashlib import sha256
from io import StringIO
from pathlib import Path
import re

from .models import Transaction, parse_amount_to_cents


BIC_PREFIX_RE = re.compile(r"^[A-Z0-9]{8}([A-Z0-9]{3})?\s+")
IBAN_PREFIX_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}\s+")
CARD_NARRATIVE_PREFIXES = (
    "bezahlung karte",
    "auszahlung karte",
    "kartenzahlung",
    "bargeldbezug",
)


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
        source_record = serialize_csv_row(row)

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
                raw_description=narrative,
                source_record=source_record,
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


def serialize_csv_row(row: list[str]) -> str:
    """Serialize parsed fields back into one complete BAWAG CSV record."""
    output = StringIO()
    writer = csv.writer(output, delimiter=";", lineterminator="")
    writer.writerow(row)
    return output.getvalue()


def strip_bank_identifiers(segment: str) -> str:
    """
    Strip a leading BIC and/or IBAN token from a narrative segment.

    Some segments have both identifiers, some only an IBAN, and some
    neither.
    """
    text = segment.strip()

    bic_match = BIC_PREFIX_RE.match(text)
    if bic_match:
        text = text[bic_match.end():]

    iban_match = IBAN_PREFIX_RE.match(text)
    if iban_match:
        text = text[iban_match.end():]

    return text.strip()


def parse_transfer_narrative(raw: str) -> tuple[str, str]:
    """
    Parse transfers, standing orders, and direct debits.

    The counterparty is the final pipe-separated segment, with leading
    bank identifiers removed.
    """
    segments = [segment.strip() for segment in raw.split("|")]
    counterparty = strip_bank_identifiers(segments[-1])
    return counterparty, ""


def parse_narrative(raw: str) -> tuple[str, str]:
    """Dispatch to card or transfer parsing based on the narrative prefix."""
    stripped = raw.strip()
    if stripped.casefold().startswith(CARD_NARRATIVE_PREFIXES):
        return parse_card_narrative(raw)
    return parse_transfer_narrative(raw)

def parse_card_narrative(raw: str) -> tuple[str, str]:
    segments = [s.strip() for s in raw.split("|")]

    if len(segments) > 1:
        terminal_info = segments[1].upper()
        if terminal_info.startswith("AUTOMAT") or terminal_info.startswith("QUICK-L"):
            return "ATM Withdrawal", segments[1]

    if len(segments) < 3:
        return "", raw.strip()

    merchant_field = segments[2]
    parts = [p for p in merchant_field.split("\\") if p.strip()]
    merchant = parts[0].strip() if parts else merchant_field
    city = parts[1].strip() if len(parts) > 1 else ""
    return merchant, city


def parse_transfer_narrative(raw: str) -> tuple[str, str]:
    stripped_raw = raw.strip()
    segments = [s.strip() for s in raw.split("|")]

    # These two narrative types have a fixed, different shape — the
    # counterparty concept doesn't really apply, so name the *type*
    # of transaction instead of guessing at a merchant.
    if stripped_raw.startswith("SB-Eigenerlag"):
        return "Cash Deposit", segments[-1] if len(segments) > 1 else ""
    if stripped_raw.startswith("Depotentgelt"):
        return "Depotentgelt", segments[1] if len(segments) > 1 else ""

    # General case: the counterparty could be in any segment after
    # segment 0, possibly with a BIC/IBAN glued on, possibly followed
    # by an unrelated purpose-text segment. Strip bank identifiers from
    # every candidate, then take whichever has the most letters left —
    # reference codes and purpose text are short/numeric, real names
    # and company names have actual words in them.
    candidates = [strip_bank_identifiers(s) for s in segments[1:]]
    if not candidates:
        return "", ""

    best = max(candidates, key=lambda c: sum(ch.isalpha() for ch in c))
    return best, ""