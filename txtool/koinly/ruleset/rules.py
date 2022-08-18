from txtool.harmony import HarmonyToken
from .types import *  # pylint: disable=W0401, W0614
from .constants import *  # pylint: disable=W0401, W0614

KOINLY_LABEL_RULES: Dict[KoinlyLabel, T_KOINLY_LABEL_RULESET] = {
    KoinlyLabel.COST: [
        (
            "Contract interaction fee",
            {
                "sent_amount": ("==", noop, 0),
                "got_amount": ("==", noop, 0),
                "tx_fee_in_native_token": ("==", bool, True),
                # "sent_currency_symbol": (
                #     "==",
                #     noop,
                #     HarmonyToken.get_native_token().symbol,
                # ),
            },
        )
    ],
    KoinlyLabel.INCOME: [
        (
            "Got JENN from gem mine",
            {
                "from_addr": ("==", noop, TOKEN_JENNY_GEM_MINE_CONTRACT_ADDRESS),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
            },
        )
    ],
}
