from enum import Enum


class TokenTaxLabel(str, Enum):
    """
    See more: https://help.tokentax.co/en/articles/1707630-create-a-manual-csv-report-of-your-transactions
    """
    TRADE = "Trade"
    DEPOSIT = "Deposit"
    WITHDRAW = "Withdrawal"
    INCOME = "Income"
    SPEND = "Spend"
    LOST = "Lost"
    STOLEN = "Stolen"
    MINING = "Mining"
    GIFT = "Gift"
    NULL = ""


