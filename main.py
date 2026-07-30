from pathlib import Path

from expense_tracker import Account, load_bawag_csv


CSV_PATH = Path("data/BAWAG_Umsatzliste_20260729_0723.csv")


def main() -> None:
    account = Account(
        id="bawag",
        name="BAWAG",
    )

    transactions = load_bawag_csv(
        CSV_PATH,
        account_id=account.id,
    )

    expenses = sum(
        transaction.amount_cents
        for transaction in transactions
        if transaction.is_expense
    )
    income = sum(
        transaction.amount_cents
        for transaction in transactions
        if transaction.is_income
    )

    print(f"Imported {len(transactions)} transactions for {account.name}")
    print(f"Expenses: {expenses / 100:.2f} {account.currency}")
    print(f"Income: {income / 100:.2f} {account.currency}")
    print(f"Net: {(income + expenses) / 100:.2f} {account.currency}")


if __name__ == "__main__":
    main()
