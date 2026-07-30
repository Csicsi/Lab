from datetime import date
from pathlib import Path

import pytest

from expense_tracker import (
    Category,
    CategoryRule,
    Transaction,
    categorize_transaction,
    categorize_transactions,
    load_categorization_config,
    normalize_text,
    transaction_search_text,
)

CONFIG_PATH = Path(__file__).parent / "fixtures" / "categories.toml"


@pytest.fixture
def default_rules() -> tuple[CategoryRule, ...]:
    _, rules = load_categorization_config(CONFIG_PATH)
    return rules


def make_transaction(
    title: str,
    city: str = "",
    raw_description: str = "",
) -> Transaction:
    return Transaction(
        id="account:source",
        account_id="account",
        source_id="source",
        booking_date=date(2026, 7, 30),
        amount_cents=-1000,
        title=title,
        city=city,
        raw_description=raw_description,
    )


def test_categorize_transaction_uses_configured_rules(
    default_rules: tuple[CategoryRule, ...],
) -> None:
    transaction = make_transaction("BILLA", "Wien")

    assert categorize_transaction(transaction, default_rules) == "groceries"


def test_categorize_transaction_is_case_insensitive(
    default_rules: tuple[CategoryRule, ...],
) -> None:
    transaction = make_transaction("Kontoführung")

    assert categorize_transaction(transaction, default_rules) == "fees"


def test_categorize_transaction_uses_first_matching_rule() -> None:
    transaction = make_transaction("BILLA")
    rules = (
        CategoryRule("shopping", ("BILLA",)),
        CategoryRule("groceries", ("BILLA",)),
    )

    assert categorize_transaction(transaction, rules) == "shopping"


def test_categorize_transaction_returns_none_without_match(
    default_rules: tuple[CategoryRule, ...],
) -> None:
    transaction = make_transaction("Unknown merchant")

    assert categorize_transaction(transaction, default_rules) is None


def test_normalize_text_normalizes_unicode_case_and_whitespace() -> None:
    assert normalize_text("  ÖBB\t WIEN  ") == "öbb wien"


def test_transaction_search_text_uses_title_and_city() -> None:
    transaction = make_transaction("  Wiener   Linien ", " WIEN ")

    assert transaction_search_text(transaction) == "wiener linien wien"


def test_transaction_search_text_prefers_full_description() -> None:
    transaction = make_transaction(
        title="Truncated reference",
        raw_description="Payment details|BILLA FIL. 1234|Reference",
    )

    assert transaction_search_text(transaction) == ("payment details|billa fil. 1234|reference")


def test_categorization_matches_full_description(
    default_rules: tuple[CategoryRule, ...],
) -> None:
    transaction = make_transaction(
        title="Truncated reference",
        raw_description="Payment details|BILLA FIL. 1234|Reference",
    )

    assert categorize_transaction(transaction, default_rules) == "groceries"


def test_categorize_transactions_returns_updated_copies(
    default_rules: tuple[CategoryRule, ...],
) -> None:
    original = make_transaction("BILLA")

    categorized = categorize_transactions([original], default_rules)

    assert categorized[0].category_id == "groceries"
    assert categorized[0] is not original
    assert original.category_id is None


def test_load_categorization_config() -> None:
    categories, rules = load_categorization_config(CONFIG_PATH)

    assert Category(id="groceries", name="Groceries") in categories
    groceries_rule = next(rule for rule in rules if rule.category_id == "groceries")
    assert "BILLA" in groceries_rule.patterns


def test_config_rejects_rules_for_unknown_categories(tmp_path: Path) -> None:
    config_path = tmp_path / "categories.toml"
    config_path.write_text('[[rules]]\ncategory_id = "missing"\npatterns = ["SHOP"]\n')

    with pytest.raises(
        ValueError,
        match="Rules reference unknown category IDs: missing",
    ):
        load_categorization_config(config_path)
