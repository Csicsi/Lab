from datetime import date

from expense_tracker import (
    Account,
    Transaction,
    parse_amount_to_cents,
)


def main() -> None:
    account = Account(
        id="bawag",
        name="BAWAG"
    )

    transaction = Transaction(
        id="bawag:123456",
        account_id=account.id,
        source_id="123456",
        booking_date=date.today(),
        amount_cents=parse_amount_to_cents("-15,49"),
        title="BILLA",
    )

    print(account)
    print(transaction)
    print(transaction.is_expense)
    print(transaction.amount_cents)


if __name__ == "__main__":
    main()