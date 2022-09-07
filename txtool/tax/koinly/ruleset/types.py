from enum import Enum


class KoinlyLabel(str, Enum):
    """
    See more: https://help.koinly.io/en/articles/3663453-what-are-labels
    """

    COST = "cost"
    INCOME = "income"
    REWARD = "reward"
    SWAP = "swap"
    NULL = ""
