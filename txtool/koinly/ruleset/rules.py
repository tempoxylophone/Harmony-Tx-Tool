from typing import Dict

from txtool.activity.services.TranquilFinance import (
    TranquilFinanceStakingEditor,
    TRANQUIL_DEPOSIT_COLLATERAL_ADDRESSES,
    TRANQUIL_COLLECT_REWARD_ADDRESSES,
)
from txtool.activity.services.ViperSwap import ViperSwapClaimRewardsEditor

from .types import T_KOINLY_LABEL_RULESET, KoinlyLabel, noop
from .constants import (
    TOKEN_JENNY_GEM_MINE_CONTRACT_ADDRESS_STR,
    CURVE_REWARD_GAUGE_DEPOSIT_CONTRACT_ADDRESS_STR,
)

KOINLY_LABEL_RULES: Dict[KoinlyLabel, T_KOINLY_LABEL_RULESET] = {
    KoinlyLabel.SWAP: [
        (
            "unwrap wsWAGMI to become sWAGMI",
            {
                "method": ("==", noop, "unwrap(uint256)"),
                "sent_currency_symbol": ("==", noop, "wsWAGMI"),
                "got_currency_symbol": ("==", noop, "sWAGMI"),
            },
        ),
        (
            "wrap sWAGMI to become wsWAGMI",
            {
                "method": ("==", noop, "wrap(uint256)"),
                "got_currency_symbol": ("==", noop, "wsWAGMI"),
                "sent_currency_symbol": ("==", noop, "sWAGMI"),
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
                "sent_currency_symbol": ("==", noop, "WAGMI"),
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
                "got_currency_symbol": ("==", noop, "WAGMI"),
                "sent_currency_symbol": ("==", noop, "sWAGMI"),
            },
        ),
    ],
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
                "got_amount": (">", noop, 0),
                "got_currency_symbol": ("in", noop, "bWAGMI"),
            },
        ),
        (
            "Stake LP Position in Curve USD-BTC-ETH Pool",
            {
                "method": (
                    "==",
                    noop,
                    "deposit(uint256)",
                ),
                "sent_currency_symbol": ("==", noop, "crvUSDBTCETH"),
                "to_addr_str": (
                    "==",
                    noop,
                    "0xF98450B5602fa59CC66e1379DFfB6FDDc724CfC4",
                ),
            },
        ),
        (
            "Unstake LP Position in Curve USD-BTC-ETH Pool",
            {
                "method": (
                    "==",
                    noop,
                    "withdraw(uint256)",
                ),
                "sent_currency_symbol": ("==", noop, "crvUSDBTCETH-gauge"),
                "to_addr_str": (
                    "==",
                    noop,
                    "0xF98450B5602fa59CC66e1379DFfB6FDDc724CfC4",
                ),
            },
        ),
        (
            "Stake LP Position in Curve 3 Pool",
            {
                "method": (
                    "==",
                    noop,
                    "deposit(uint256)",
                ),
                "sent_currency_symbol": ("==", noop, "3CRV"),
                "to_addr_str": (
                    "==",
                    noop,
                    "0xbF7E49483881C76487b0989CD7d9A8239B20CA41",
                ),
            },
        ),
        (
            "Unstake LP Position in Curve 3 Pool",
            {
                "method": (
                    "==",
                    noop,
                    "withdraw(uint256)",
                ),
                "got_currency_symbol": ("==", noop, "3CRV"),
                "sent_currency_symbol": ("==", noop, "3CRV-gauge"),
                "got_amount": (">", noop, 0),
                "sent_amount": (">", noop, 0),
                "to_addr_str": (
                    "==",
                    noop,
                    "0xbF7E49483881C76487b0989CD7d9A8239B20CA41",
                ),
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
                "to_addr_str": (
                    "in",
                    noop,
                    ViperSwapClaimRewardsEditor.CONTRACT_ADDRESSES,
                ),
            },
        ),
        (
            "Exit LP Position",
            {
                "method": (
                    "in",
                    lambda x: x.split("(", maxsplit=1)[0],
                    ("removeLiquidity", "withdraw"),
                ),
                "got_amount": (">", noop, 0),
                "got_currency_is_lp_token": (
                    "==",
                    noop,
                    True,
                ),
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
                "sent_amount": (">", noop, 0),
            },
        ),
        (
            "Stake TRANQ in Tranquil Finance",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": ("==", noop, 0),
                "to_addr_str": (
                    "in",
                    noop,
                    TranquilFinanceStakingEditor.CONTRACT_ADDRESSES,
                ),
                "sent_currency_symbol": ("==", noop, "TRANQ"),
                "method": ("==", noop, "deposit(uint256)"),
            },
        ),
        (
            "Unstake TRANQ from Tranquil Finance",
            {
                "sent_amount": ("==", noop, 0),
                "got_amount": (">", noop, 0),
                "from_addr_str": (
                    "in",
                    noop,
                    TranquilFinanceStakingEditor.CONTRACT_ADDRESSES,
                ),
                "got_currency_symbol": ("==", noop, "TRANQ"),
                "method": ("==", noop, "redeem(uint256)"),
            },
        ),
        (
            "Borrow from Tranquil Finance",
            {
                "sent_amount": ("==", noop, 0),
                "got_amount": (">", noop, 0),
                "from_addr_str": ("in", noop, TRANQUIL_DEPOSIT_COLLATERAL_ADDRESSES),
                "method": ("==", noop, "borrow(uint256)"),
            },
        ),
        (
            "Repay borrow to Tranquil Finance",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": ("==", noop, 0),
                "to_addr_str": (
                    "in",
                    noop,
                    TRANQUIL_DEPOSIT_COLLATERAL_ADDRESSES,
                ),
                "method": ("==", noop, "repayBorrow(uint256)"),
            },
        ),
        (
            "Deposit collateral into Tranquil Finance",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": (">", noop, 0),
                "got_currency_symbol": ("==", lambda x: str(x)[:2], "tq"),
                "method": ("in", lambda x: str(x).split("(", maxsplit=1)[0], "mint"),
                "to_addr_str": (
                    "in",
                    noop,
                    TRANQUIL_DEPOSIT_COLLATERAL_ADDRESSES,
                ),
            },
        ),
        (
            "Remove collateral from Tranquil Finance",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": (">", noop, 0),
                "sent_currency_symbol": ("==", lambda x: str(x)[:2], "tq"),
                "method": ("==", noop, "redeem(uint256)"),
            },
        ),
        (
            "Got NFT in Trade",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": (">", noop, 0),
                "got_currency_is_nft": ("==", noop, True),
            },
        ),
        (
            "Sent NFT in Trade",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": (">", noop, 0),
                "sent_currency_is_nft": ("==", noop, True),
            },
        ),
        (
            "Trade",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": (">", noop, 0),
            },
        ),
        (
            "Wallet to Wallet HRC20 Token Transfer",
            {
                "sent_amount": (">", noop, 0),
                "got_amount": ("==", noop, 0),
                "method": ("==", noop, "transfer(address,uint256)"),
            },
        ),
    ],
    KoinlyLabel.COST: [
        (
            "Contract interaction fee",
            {
                "sent_amount": ("==", noop, 0),
                "got_amount": ("==", noop, 0),
                "tx_fee_in_native_token": (">", noop, 0),
            },
        ),
            (
            "Horizon Bridge fee",
            {
                "sent_amount": (">", noop, 0),
                "to_addr_str": ("==", noop, "0x8139d578f11638C78E16685EB2804c2a34482E41"),
                "method": ("==", noop, "deposit(uint256)")
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
            "Unlock locked VIPER",
            {
                "from_addr_str": (
                    "==",
                    noop,
                    "0xEa589E93Ff18b1a1F1e9BaC7EF3E86Ab62addc79",
                ),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
                "got_currency_symbol": ("==", noop, "VIPER"),
                "method": ("==", noop, "unlock()")
            },
        ),
        (
            "Claim TRANQ reward",
            {
                "from_addr_str": (
                    "in",
                    noop,
                    TRANQUIL_COLLECT_REWARD_ADDRESSES,
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
                    "in",
                    noop,
                    ViperSwapClaimRewardsEditor.CONTRACT_ADDRESSES,
                ),
                "is_receiver": ("==", noop, True),
                "got_amount": (">", noop, 0),
                "method": (
                    "in",
                    noop,
                    (
                        "claimReward(uint256)",
                        "claimRewards(uint256[])",
                        "deposit(uint256,uint256,address)",
                        "withdraw(uint256,uint256,address)",
                    ),
                ),
            },
        ),
    ],
}
