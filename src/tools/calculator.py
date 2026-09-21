def calculate_income(transactions):
    income = 0

    for transaction in transactions:
        amount = transaction["amount"]

        if amount > 0:
            income += amount

    return income


def calculate_expenses(transactions):
    expenses = 0

    for transaction in transactions:
        amount = transaction["amount"]

        if amount < 0:
            expenses += abs(amount)

    return expenses


def calculate_remaining(income, expenses):
    return income - expenses