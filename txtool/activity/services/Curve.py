from typing import List

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class Curve3PoolLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Curve.fi DAI/USDC/USDT
        "0xC5cfaDA84E902aD92DD40194f0883ad49639b023",
        # Curve.fi 3CRV RewardGauge Deposit
        "0xbF7E49483881C76487b0989CD7d9A8239B20CA41"
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "claim_rewards(address)":
            return self.parse_claim_rewards(transactions)
        if root_method == "add_liquidity(uint256[3],uint256)":
            return self.parse_add_liquidity(transactions)
        if root_method == "remove_liquidity(uint256,uint256[3])":
            return self.parse_remove_liquidity(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_claim_rewards(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(transactions)

    def parse_add_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # USDC/DAI/USDT -> 3CRV
        liquidity_received_tx = transactions[-1]
        i_1, i_2, i_3 = self.split_copy(liquidity_received_tx, 3)
        o_1, o_2, o_3 = transactions[1:4]

        return InterpretedTransactionGroup(
            [
                transactions[0],
                self.consolidate_trade(o_1, i_1),
                self.consolidate_trade(o_2, i_2),
                self.consolidate_trade(o_3, i_3),
            ]
        )

    def parse_remove_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # 3CRV -> USDC/DAI/USDT
        liquidity_give_tx = transactions[-1]

        # overwrite null address to CURVE contract
        liquidity_give_tx.to_addr = transactions[0].to_addr

        o_1, o_2, o_3 = self.split_copy(liquidity_give_tx, 3)
        i_1, i_2, i_3 = transactions[1:4]

        return InterpretedTransactionGroup(
            [
                transactions[0],
                self.consolidate_trade(o_1, i_1),
                self.consolidate_trade(o_2, i_2),
                self.consolidate_trade(o_3, i_3),
            ]
        )
