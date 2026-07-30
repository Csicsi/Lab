from pathlib import Path

from expense_tracker import (
    Account,
    categorize_transactions,
    load_bawag_csv,
    load_categorization_config,
)

CSV_PATH = Path("data/BAWAG_Umsatzliste_20260729_0723.csv")
CATEGORIZATION_CONFIG_PATH = Path("config/categories.toml")
UNCATEGORIZED_REPORT_PATH = Path("uncategorized_transactions.txt")
CATEGORY_AUDIT_PATH = Path("category_audit.txt")


def main() -> None:
    account = Account(
        id="bawag",
        name="BAWAG",
    )
    categories, category_rules = load_categorization_config(CATEGORIZATION_CONFIG_PATH)

    transactions = load_bawag_csv(
        CSV_PATH,
        account_id=account.id,
    )
    transactions = categorize_transactions(transactions, category_rules)

    expenses = sum(
        transaction.amount_cents for transaction in transactions if transaction.is_expense
    )
    income = sum(transaction.amount_cents for transaction in transactions if transaction.is_income)

    print(f"Imported {len(transactions)} transactions for {account.name}")
    print(f"Expenses: {expenses / 100:.2f} {account.currency}")
    print(f"Income: {income / 100:.2f} {account.currency}")
    print(f"Net: {(income + expenses) / 100:.2f} {account.currency}")

    print("\nExpenses by category:")
    for category in categories:
        category_total = sum(
            -transaction.amount_cents
            for transaction in transactions
            if transaction.is_expense and transaction.category_id == category.id
        )
        if category_total:
            print(f"  {category.name}: {category_total / 100:.2f} {account.currency}")

    uncategorized = [transaction for transaction in transactions if transaction.category_id is None]
    uncategorized_expenses = sum(
        -transaction.amount_cents for transaction in uncategorized if transaction.is_expense
    )
    uncategorized_income = sum(
        transaction.amount_cents for transaction in uncategorized if transaction.is_income
    )
    categorized_expenses = sum(
        -transaction.amount_cents
        for transaction in transactions
        if transaction.category_id is not None and transaction.is_expense
    )
    categorized_income = sum(
        transaction.amount_cents
        for transaction in transactions
        if transaction.category_id is not None and transaction.is_income
    )
    total_expenses = -expenses

    expenses_reconcile = categorized_expenses + uncategorized_expenses == total_expenses
    income_reconcile = categorized_income + uncategorized_income == income

    print(f"\nUncategorized transactions: {len(uncategorized)}")
    print(f"Uncategorized expenses: {uncategorized_expenses / 100:.2f} {account.currency}")
    print(f"Uncategorized income: {uncategorized_income / 100:.2f} {account.currency}")
    print("\nReconciliation:")
    print(
        f"  Expenses: categories "
        f"{categorized_expenses / 100:.2f} + uncategorized "
        f"{uncategorized_expenses / 100:.2f} = "
        f"{total_expenses / 100:.2f} {account.currency} "
        f"[{'OK' if expenses_reconcile else 'MISMATCH'}]"
    )
    print(
        f"  Income: categories "
        f"{categorized_income / 100:.2f} + uncategorized "
        f"{uncategorized_income / 100:.2f} = "
        f"{income / 100:.2f} {account.currency} "
        f"[{'OK' if income_reconcile else 'MISMATCH'}]"
    )
    if not expenses_reconcile or not income_reconcile:
        raise RuntimeError("Category totals do not reconcile")

    report_entries = [
        "\n".join(
            (
                f"Date: {transaction.booking_date}",
                (f"Amount: {transaction.amount_cents / 100:.2f} {account.currency}"),
                f"Title: {transaction.title}",
                f"Full description: {transaction.raw_description}",
                f"CSV: {transaction.source_record}",
            )
        )
        for transaction in uncategorized
    ]
    UNCATEGORIZED_REPORT_PATH.write_text(
        "\n\n---\n\n".join(report_entries) + "\n",
        encoding="utf-8",
    )
    print(f"Saved full details to {UNCATEGORIZED_REPORT_PATH}")

    audit_sections: list[str] = []
    category_groups = [
        (
            category.name,
            [transaction for transaction in transactions if transaction.category_id == category.id],
        )
        for category in categories
    ]
    category_groups.append(("Uncategorized", uncategorized))

    for category_name, category_transactions in category_groups:
        category_expenses = sum(
            -transaction.amount_cents
            for transaction in category_transactions
            if transaction.is_expense
        )
        category_income = sum(
            transaction.amount_cents
            for transaction in category_transactions
            if transaction.is_income
        )
        lines = [
            f"Category: {category_name}",
            f"Transactions: {len(category_transactions)}",
            (f"Expenses: {category_expenses / 100:.2f} {account.currency}"),
            f"Income: {category_income / 100:.2f} {account.currency}",
            "",
        ]
        audit_sections.append("\n".join(lines).rstrip())

    CATEGORY_AUDIT_PATH.write_text(
        ("\n\n" + ("=" * 80) + "\n\n").join(audit_sections) + "\n",
        encoding="utf-8",
    )
    print(f"Saved category audit to {CATEGORY_AUDIT_PATH}")


if __name__ == "__main__":
    main()
