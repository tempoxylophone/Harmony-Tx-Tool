from typing import List

from txtool.harmony import (
    WalletActivity,
)
from .services.common import InterpretedTransactionGroup
from .services.Curve import Curve3PoolLiquidityEditor
from .services.TranquilFinance import TranquilFinanceEditor
from .services.Euphoria import EuphoriaBondEditor
from .services.ViperSwap import (
    ViperSwapXRewardsEditor,
    ViperSwapLiquidityEditor,
    ViperSwapClaimRewardsEditor,
)

EDITORS = [
    # ViperSwap
    ViperSwapClaimRewardsEditor(),
    ViperSwapXRewardsEditor(),
    ViperSwapLiquidityEditor(),
    # Euphoria
    EuphoriaBondEditor(),
    # Tranquil
    TranquilFinanceEditor(),
    # Curve
    Curve3PoolLiquidityEditor(),
]


def interpret_multi_transaction(
    transactions: List[WalletActivity],
) -> InterpretedTransactionGroup:
    for t in EDITORS:
        # try all interpreters, if find a relevant one, interpret the txs
        if t.should_interpret(transactions):
            return t.interpret(transactions)

    return InterpretedTransactionGroup(transactions)


def get_interpreted_transaction_from_hash(
    tx_hash: str,
) -> InterpretedTransactionGroup:
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(tx_hash)
    return InterpretedTransactionGroup(interpret_multi_transaction(txs))
