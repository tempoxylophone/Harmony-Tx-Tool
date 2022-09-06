from typing import List

from txtool.harmony import (
    HarmonyAddress,
    WalletActivity,
)
from .services.common import InterpretedTransactionGroup
from .services.Curve import Curve3PoolLiquidityEditor, CurveUSDBTCETHLiquidityEditor
from .services.TranquilFinance import (
    TranquilFinanceEditor,
    TranquilFinanceONEDepositEditor,
    TranquilFinanceStakingEditor,
)
from .services.Euphoria import EuphoriaBondEditor, EuphoriaWrapEditor
from .services.ViperSwap import (
    ViperSwapXRewardsEditor,
    ViperSwapLiquidityEditor,
    ViperSwapClaimRewardsEditor,
)
from .services.SushiSwap import SushiSwapLiquidityEditor
from .services.DefiKingdoms import DefiKingdomsLiquidityEditor, DefiKingdomsClaimsEditor

EDITORS = [
    # ViperSwap
    ViperSwapClaimRewardsEditor(),
    ViperSwapXRewardsEditor(),
    ViperSwapLiquidityEditor(),
    # SushiSwap
    SushiSwapLiquidityEditor(),
    # Defi Kingdoms
    DefiKingdomsLiquidityEditor(),
    DefiKingdomsClaimsEditor(),
    # Euphoria
    EuphoriaBondEditor(),
    EuphoriaWrapEditor(),
    # Tranquil
    TranquilFinanceEditor(),
    TranquilFinanceONEDepositEditor(),
    TranquilFinanceStakingEditor(),
    # Curve
    Curve3PoolLiquidityEditor(),
    CurveUSDBTCETHLiquidityEditor(),
]


def interpret_multi_transaction(
    transactions: List[WalletActivity],
) -> InterpretedTransactionGroup:
    for t in EDITORS:
        # try all interpreters, if find a relevant one, interpret the txs
        if t.should_interpret(transactions):
            return t.interpret(transactions)

    return InterpretedTransactionGroup(transactions)


def get_interpreted_transactions(
    account: HarmonyAddress,
    tx_hash: str,
) -> InterpretedTransactionGroup:
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(account, tx_hash)
    return interpret_multi_transaction(txs)
