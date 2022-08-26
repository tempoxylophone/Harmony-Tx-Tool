from typing import List
from copy import deepcopy

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class Curve3PoolLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        "0xC5cfaDA84E902aD92DD40194f0883ad49639b023",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) != 5:
            return InterpretedTransactionGroup(transactions)

        # interpret 3 pool liquidity add
        results = [transactions[0]]

        liquidity_received_tx = transactions[1]

        if liquidity_received_tx.method == "add_liquidity(uint256[3],uint256)":
            # add liquidity
            is_remove = False
        elif liquidity_received_tx.method == "remove_liquidity(uint256,uint256[3])":
            # remove liquidity
            is_remove = True
        else:
            # unknown method signature - do nothing
            return InterpretedTransactionGroup(transactions)

        p_size_name = "sent_amount" if is_remove else "got_amount"

        lp_position_size = getattr(liquidity_received_tx, p_size_name) / 3

        for i in range(3):
            # copy original token transfer tx, give 3 transfer tx
            # where LP position is 1/3rd of full position
            d = deepcopy(liquidity_received_tx)

            # edit amounts to add / remove
            d.coin_amount = lp_position_size
            setattr(d, p_size_name, lp_position_size)

            # order matters depending on add / remove
            t_group = [d, transactions[i + 2]]
            if is_remove:
                t_group = list(reversed(t_group))

            results += t_group

        # write tx logs in order
        for i, x in enumerate(results):
            x.log_idx = i

        return InterpretedTransactionGroup(results)
