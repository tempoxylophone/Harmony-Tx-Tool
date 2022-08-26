from typing import List
from decimal import Decimal

from txtool.harmony import (
    HarmonyToken,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class TranquilFinanceEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Unitroller
        "0x6a82A17B48EF6be278BBC56138F35d04594587E3",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) > 1 and all(
            isinstance(x.got_currency, HarmonyToken)
            and x.got_currency.symbol == "TRANQ"
            for x in transactions[1:]
        ):
            # leaf txs are just transfers to caller of some amount of TRANQ
            to_merge = transactions[1:]

            total_reward = Decimal(sum(x.got_amount for x in to_merge) or 0)
            reward_tx = to_merge[0]
            reward_tx.got_amount = total_reward
            reward_tx.coin_amount = total_reward

            return InterpretedTransactionGroup(
                [
                    # the cost transaction
                    transactions[0],
                    # all deposits from TRANQ rewards
                    reward_tx,
                ]
            )

        return InterpretedTransactionGroup(transactions)
