from .types import *  # pylint: disable=W0401, W0614
from .constants import *  # pylint: disable=W0401, W0614

KOINLY_LABEL_RULES: Dict[KoinlyLabel, T_KOINLY_LABEL_RULESET] = {
    KoinlyLabel.NULL: [
        (
            "Stake TRANQ in Tranquil Finance",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": ("==", noop, 0),
                "to_addr_str": ("==", noop, TRANQUIL_FINANCE_STAKING_PROXY_ADDRESS_STR),
                "sent_currency_symbol": ("==", noop, "TRANQ"),
                "method": ("==", noop, "deposit(uint256)"),
            },
        ),
        (
            "Borrow from Tranquil Finance",
            {
                "sent_amount": ("==", noop, 0),
                "got_amount": (">", noop, 0),
                "from_addr_str": (
                    "==",
                    noop,
                    TRANQUIL_FINANCE_TQ_ERC20_DELEGATOR_ADDRESS_STR,
                ),
                "method": ("==", noop, "borrow(uint256)"),
            },
        ),
        (
            "Repay borrow to Tranquil Finance",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": ("==", noop, 0),
                "to_addr_str": (
                    "==",
                    noop,
                    TRANQUIL_FINANCE_TQ_ERC20_DELEGATOR_ADDRESS_STR,
                ),
                "method": ("==", noop, "repayBorrow(uint256)"),
            },
        ),
        (
            "Remove collateral from Tranquil Finance",
            {
                "sent_amount": ("==", noop, 0),
                "got_amount": (">", noop, 0),
                "from_addr_str": (
                    "==",
                    noop,
                    TRANQUIL_FINANCE_TQ_ERC20_DELEGATOR_ADDRESS_STR,
                ),
                "method": ("==", noop, "redeem(uint256)"),
            },
        ),
    ],
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
        ),
        (
            "Claim CRV rewards",
            {
                "from_addr_str": (
                    "==",
                    noop,
                    CURVE_REWARD_GAUGE_DEPOSIT_CONTRACT_ADDRESS_STR,
                ),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
                "method": ("==", noop, "claim_rewards(address)"),
            },
        ),
    ],
}
