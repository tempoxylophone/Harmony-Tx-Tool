from typing import Tuple, Type, Dict, List, Any, Callable, Union
from enum import Enum
import operator


class KoinlyLabel(str, Enum):
    """
    See more: https://help.koinly.io/en/articles/3663453-what-are-labels
    """

    COST = "cost"
    INCOME = "income"
    REWARD = "reward"
    NULL = ""


OPERATORS: Dict[str, Callable] = {
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
}

T_KOINLY_LABEL_RULESET = List[
    Tuple[
        # associated description
        str,
        # potential properties that match this label
        Dict[str, Tuple[str, Union[Type, Callable], Any]],
    ]
]


def noop(x: Any) -> Any:
    return x
