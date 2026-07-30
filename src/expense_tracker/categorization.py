from __future__ import annotations

import tomllib
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .models import Category, Transaction


def normalize_text(value: str) -> str:
    """Normalize text for predictable, case-insensitive rule matching."""
    unicode_normalized = unicodedata.normalize("NFKC", value)
    return " ".join(unicode_normalized.casefold().split())


def transaction_search_text(transaction: Transaction) -> str:
    """Build searchable text from the fields used by category rules."""
    description = transaction.raw_description or transaction.title
    return normalize_text(f"{description} {transaction.city}")


@dataclass(frozen=True)
class CategoryRule:
    """Assign a category when any pattern occurs in the transaction text."""

    category_id: str
    patterns: tuple[str, ...]

    def matches(self, transaction: Transaction) -> bool:
        searchable_text = transaction_search_text(transaction)
        return any(normalize_text(pattern) in searchable_text for pattern in self.patterns)


def load_categorization_config(
    path: str | Path,
) -> tuple[tuple[Category, ...], tuple[CategoryRule, ...]]:
    """Load categories and ordered matching rules from a TOML file."""
    with Path(path).open("rb") as config_file:
        data = tomllib.load(config_file)

    categories = tuple(Category.model_validate(item) for item in data.get("categories", []))
    category_ids = [category.id for category in categories]
    if len(category_ids) != len(set(category_ids)):
        raise ValueError("Category IDs must be unique")

    rules = tuple(
        CategoryRule(
            category_id=item["category_id"],
            patterns=tuple(item["patterns"]),
        )
        for item in data.get("rules", [])
    )
    unknown_ids = {rule.category_id for rule in rules if rule.category_id not in category_ids}
    if unknown_ids:
        unknown = ", ".join(sorted(unknown_ids))
        raise ValueError(f"Rules reference unknown category IDs: {unknown}")

    return categories, rules


def categorize_transaction(
    transaction: Transaction,
    rules: Sequence[CategoryRule],
) -> str | None:
    """Return the category from the first matching rule."""
    return next(
        (rule.category_id for rule in rules if rule.matches(transaction)),
        None,
    )


def categorize_transactions(
    transactions: Sequence[Transaction],
    rules: Sequence[CategoryRule],
) -> list[Transaction]:
    """Return categorized copies without mutating the input transactions."""
    return [
        transaction.model_copy(update={"category_id": categorize_transaction(transaction, rules)})
        for transaction in transactions
    ]
