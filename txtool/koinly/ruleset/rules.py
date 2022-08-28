from typing import Dict
from .types import T_KOINLY_LABEL_RULESET, KoinlyLabel, noop
from .constants import (
    TRANQUIL_FINANCE_STAKING_PROXY_ADDRESS_STR,
    TRANQUIL_FINANCE_TQ_ERC20_DELEGATOR_ADDRESS_STR,
    TRANQUIL_FINANCE_COMPTROLLER_CONTRACT_ADDRESS_STR,
    TOKEN_JENNY_GEM_MINE_CONTRACT_ADDRESS_STR,
    VIPERSWAP_CLAIM_VIPER_CONTRACT_ADDRESS_STR,
    CURVE_REWARD_GAUGE_DEPOSIT_CONTRACT_ADDRESS_STR,
    EUPHORIA_BOND_DEPOSITORY_CONTRACT_ADDRESS_STR,
)

KOINLY_LABEL_RULES: Dict[KoinlyLabel, T_KOINLY_LABEL_RULESET] = {
    KoinlyLabel.NULL: [
        (
            "Redeem WAGMI Bond",
            {
                "method": ("==", noop, "redeem(address,bool)"),
                "got_amount": (">", noop, 0),
                "got_currency_symbol": ("in", noop, "sWAGMI|WAGMI"),
            },
        ),
        (
            "WAGMI Bond",
            {
                "method": (
                    "==",
                    noop,
                    "deposit(uint256,uint256,address)",
                ),
                "sent_amount": (">", noop, 0),
                "to_addr_str": (
                    "==",
                    noop,
                    EUPHORIA_BOND_DEPOSITORY_CONTRACT_ADDRESS_STR,
                ),
            },
        ),
        (
            "Stake WAGMI for sWAGMI",
            {
                "method": (
                    "==",
                    noop,
                    "stake(uint256,address)",
                ),
                "sent_currency_symbol": ("==", noop, "WAGMI"),
            },
        ),
        (
            "Get sWAGMI for WAGMI staking",
            {
                "method": (
                    "==",
                    noop,
                    "stake(uint256,address)",
                ),
                "got_currency_symbol": ("==", noop, "sWAGMI"),
            },
        ),
        (
            "Unstake sWAGMI for WAGMI",
            {
                "method": (
                    "==",
                    noop,
                    "unstake(uint256,bool)",
                ),
                "sent_currency_symbol": ("==", noop, "sWAGMI"),
            },
        ),
        (
            "Get WAGMI for sWAGMI unstaking",
            {
                "method": (
                    "==",
                    noop,
                    "unstake(uint256,bool)",
                ),
                "got_currency_symbol": ("==", noop, "WAGMI"),
            },
        ),
        (
            "Stake LP Position in ViperSwap",
            {
                "method": (
                    "==",
                    noop,
                    "deposit(uint256,uint256,address)",
                ),
                "sent_currency_symbol": ("==", noop, "VENOM-LP"),
                "to_addr_str": ("==", noop, VIPERSWAP_CLAIM_VIPER_CONTRACT_ADDRESS_STR),
            },
        ),
        (
            "Enter LP Position",
            {
                "method": (
                    "==",
                    noop,
                    "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)",
                ),
                "sent_currency_symbol": ("!=", noop, "ONE"),
                "got_currency_symbol": ("!=", noop, "ONE"),
            },
        ),
        (
            "Enter LP Position with Native Token Pair",
            {
                "method": (
                    "==",
                    noop,
                    "addLiquidityETH(address,uint256,uint256,uint256,address,uint256)",
                ),
            },
        ),
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
        (
            "Trade",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": (">", noop, 0),
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
        (
            "Claim VIPER rewards",
            {
                "from_addr_str": (
                    "==",
                    noop,
                    VIPERSWAP_CLAIM_VIPER_CONTRACT_ADDRESS_STR,
                ),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
                "method": (
                    "in",
                    noop,
                    "claimReward(uint256)|claimRewards(uint256[])|deposit(uint256,uint256,address)",
                ),
            },
        ),
    ],
}
