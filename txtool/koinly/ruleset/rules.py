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
            },
        )
    ],
    KoinlyLabel.INCOME: [
        (
            "Got JENN from gem mine",
            {
                "from_addr_str": (
                    "==",
                    noop,
                    TOKEN_JENNY_GEM_MINE_CONTRACT_ADDRESS_STR,
                ),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
                "got_currency_symbol": ("==", noop, "JENN"),
            },
        )
    ],
    KoinlyLabel.REWARD: [
        (
            "Claim TRANQ reward",
            {
                "from_addr_str": (
                    "==",
                    noop,
                    TRANQUIL_FINANCE_COMPTROLLER_CONTRACT_ADDRESS_STR,
                ),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
                "got_currency_symbol": ("==", noop, "TRANQ"),
            },
        )
    ],
}
