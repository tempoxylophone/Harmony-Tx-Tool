from typing import Tuple, Type, Dict, List, Any, Callable, Union, NewType
from enum import Enum
import operator
from txtool.harmony import WalletActivity

T_LABEL_RULE = List[
    Tuple[
        # associated description
        str,
        # potential properties that match this label
        Dict[str, Tuple[str, Union[Type, Callable], Any]],
    ]
]
T_LABEL = NewType('T_LABEL', Enum)
T_LABEL_RULESET = Dict[T_LABEL, T_LABEL_RULE]

OPERATORS: Dict[str, Callable] = {
    "==": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
    "!=": operator.ne,
    "in": lambda x, y: x in y,
}


def noop(x: Any) -> Any:
    return x


def before_parens(x: str) -> str:
    return x.split("(", maxsplit=1)[0].strip()


def get_label_for_tx_and_description_with_ruleset(tx: WalletActivity, ruleset: T_LABEL_RULESET) -> Tuple[T_LABEL, str]:
    for label, rules in ruleset.items():
        for rule in rules:
            is_match = True
            desc, ruleset = rule
            for prop_name, prop_conf in ruleset.items():
                op, prop_type, prop_val = prop_conf

                # all criteria must match
                is_match = is_match and (
                    OPERATORS[op](
                        prop_type(getattr(tx, prop_name)),
                        prop_val,
                    )
                )

            if is_match:
                return label, desc

    # couldn't find a match
    return "", ""
