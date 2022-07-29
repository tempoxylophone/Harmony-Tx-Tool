from txtool.harmony import HarmonyToken
from .types import *
from .constants import *

KOINLY_LABEL_RULES: Dict[KoinlyLabel, T_KOINLY_LABEL_RULESET] = {
    KoinlyLabel.COST:
        [
            (
                "Contract interaction fee",
                {
                    'sentAmount': ("==", noop, 0),
                    'gotAmount': ("==", noop, 0),
                    'tx_fee_in_native_token': ("==", bool, True),
                    'sentCurrencySymbol': ("==", noop, HarmonyToken.native_token().symbol),
                }
            )
        ],
    KoinlyLabel.INCOME:
        [
            (
                "Got JENN from gem mine", {
                    'from_addr': ("==", noop, TOKEN_JENNY_GEM_MINE_CONTRACT_ADDRESS),
                    'is_receiver': ("==", noop, True),
                    'gotAmount': (">", noop, 0)
                }
            )
        ]
}
