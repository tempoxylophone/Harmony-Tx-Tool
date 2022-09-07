from typing import Tuple
from txtool.harmony import WalletActivity

from ...common import get_label_for_tx_and_description_with_ruleset

from .types import KoinlyLabel
from .rules import KOINLY_LABEL_RULES


def get_label_for_tx_and_description(tx: WalletActivity) -> Tuple[KoinlyLabel, str]:
    label, desc = get_label_for_tx_and_description_with_ruleset(tx, KOINLY_LABEL_RULES)
    if label == "":
        return KoinlyLabel.NULL, desc

    return label, desc


def is_cost(tx: WalletActivity) -> bool:
    label, _ = get_label_for_tx_and_description(tx)
    return label == KoinlyLabel.COST
