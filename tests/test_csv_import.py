from io import StringIO

import pytest

from expense_tracker import parse_bawag_csv


def test_parse_bawag_csv_parses_export_row() -> None:
    csv_data = StringIO(
        "AT123;"
        r"Bezahlung Karte MC/0001|POS 1234|BILLA\WIEN\1010"
        ";28.07.2026;28.07.2026;-15,49;EUR\r\n"
    )

    transactions = parse_bawag_csv(csv_data)

    assert len(transactions) == 1
    transaction = transactions[0]
    assert transaction.account_id == "AT123"
    assert transaction.id == f"AT123:{transaction.source_id}"
    assert transaction.booking_date.isoformat() == "2026-07-28"
    assert transaction.amount_cents == -1549
    assert transaction.title == "BILLA"
    assert transaction.city == "WIEN"
    assert transaction.raw_description == (r"Bezahlung Karte MC/0001|POS 1234|BILLA\WIEN\1010")
    assert transaction.source_record == (
        "AT123;"
        r"Bezahlung Karte MC/0001|POS 1234|BILLA\WIEN\1010"
        ";28.07.2026;28.07.2026;-15,49;EUR"
    )
    assert transaction.category_id is None


def test_parse_bawag_csv_accepts_application_account_id() -> None:
    csv_data = StringIO(
        "AT123;Bargeldbezug MC/0002|AUTOMAT WIEN HAUPTBAHNHOF;27.07.2026;27.07.2026;-20,00;EUR\n"
    )

    transaction = parse_bawag_csv(csv_data, account_id="bawag-main")[0]

    assert transaction.account_id == "bawag-main"
    assert transaction.title == "ATM Withdrawal"
    assert transaction.city == "AUTOMAT WIEN HAUPTBAHNHOF"
    assert transaction.category_id is None


def test_parse_bawag_csv_uses_transaction_type_as_fallback_title() -> None:
    csv_data = StringIO("AT123;Kontoführung;26.07.2026;26.07.2026;-3,00;EUR\n")

    transaction = parse_bawag_csv(csv_data)[0]

    assert transaction.title == "Kontoführung"
    assert transaction.city == ""


def test_parse_bawag_csv_rejects_rows_with_wrong_number_of_fields() -> None:
    csv_data = StringIO("AT123;Narrative;28.07.2026\n")

    with pytest.raises(ValueError, match="row 1 has 3 fields; expected 6"):
        parse_bawag_csv(csv_data)
