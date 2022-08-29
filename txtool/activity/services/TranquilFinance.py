from typing import List
from decimal import Decimal

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class TranquilFinanceEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Unitroller
        "0x6a82A17B48EF6be278BBC56138F35d04594587E3",
        # TqErc20Delegator
        "0x7af2430eFa179dB0e76257E5208bCAf2407B2468",
        # TqErc20Delegator (2)
        "0xCa3e902eFdb2a410C952Fd3e4ac38d7DBDCB8E96",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method
        if root_method == "claimReward(uint8,address)":
            return self.parse_claim_reward(transactions)
        if root_method == "mint(uint256)":
            return self.parse_mint(transactions)
        if root_method == "redeem(uint256)":
            return self.parse_redeem(transactions)
        if root_method == "borrow(uint256)":
            return self.parse_borrow(transactions)
        if root_method == "repayBorrow(uint256)":
            return self.parse_repay_borrow(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_claim_reward(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        reward_tx = transactions[1]
        reward_tx.got_amount = Decimal(sum(x.got_amount for x in transactions[1:]) or 0)
        return InterpretedTransactionGroup([transactions[0], reward_tx])

    def parse_mint(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_tx = transactions[0]
        get_tx = next(x for x in transactions[1:] if x.to_addr == root_tx.account)
        give_tx = next(x for x in transactions[1:] if x.from_addr == root_tx.account)
        return InterpretedTransactionGroup(
            [transactions[0], self.consolidate_trade(give_tx, get_tx)]
        )

    def parse_redeem(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        get_tx = transactions[1]
        give_tx = transactions[2]
        return InterpretedTransactionGroup(
            [transactions[0], self.consolidate_trade(give_tx, get_tx)]
        )

    def parse_borrow(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(transactions)

    def parse_repay_borrow(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(transactions)
