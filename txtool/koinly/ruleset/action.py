from txtool.harmony import HarmonyEVMTransaction
from .rules import *


def get_label_for_tx_and_description(tx: HarmonyEVMTransaction) -> Tuple[str, str]:
    for label, rules in KOINLY_LABEL_RULES.items():
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
    return KoinlyLabel.NULL, ""


def is_cost(tx: HarmonyEVMTransaction) -> bool:
    label, desc = get_label_for_tx_and_description(tx)
    return label == KoinlyLabel.COST
