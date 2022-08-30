from typing import List
from decimal import Decimal
from copy import deepcopy

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup
from .dex import UniswapDexEditor


class ViperSwapClaimRewardsEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Viper Rewards Contract
        "0x7AbC67c8D4b248A38B0dc5756300630108Cb48b4",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "deposit(uint256,uint256,address)":
            return self.parse_deposit(transactions)

        if root_method in ("claimRewards(uint256[])", "claimReward(uint256)"):
            return self.parse_claim_reward(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_deposit(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # add liquidity and claim rewards
        # everything after the first two is some kind of claim reward
        # when you enter an LP position you had already entered, when
        # you stake the position, you automatically claim rewards
        deposit_tx = transactions[-1]
        results = [
            transactions[0],
            deposit_tx,
        ]

        claim_txs = [x for x in transactions[1:-1] if x.is_sender or x.is_receiver]
        if claim_txs:
            results.append(self._consolidate_claims(claim_txs))

        return InterpretedTransactionGroup(results)

    def parse_claim_reward(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # claim rewards only
        return InterpretedTransactionGroup(
            [transactions[0], self._consolidate_claims(transactions[1:])]
        )

    def _consolidate_claims(self, claim_txs: List[WalletActivity]) -> WalletActivity:
        plus_tx = [
            x for x in claim_txs if x.is_receiver and x.got_currency_symbol == "VIPER"
        ]
        minus_tx = [
            x for x in claim_txs if x.is_sender and x.got_currency_symbol == "VIPER"
        ]

        consolidated_tx = deepcopy(plus_tx[0])

        delta = Decimal(
            sum(x.got_amount for x in plus_tx) + sum(x.sent_amount for x in minus_tx)
        )
        consolidated_tx.coin_amount = delta
        consolidated_tx.got_amount = delta

        return consolidated_tx


class ViperSwapXRewardsEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap ViperPit
        "0x08913d353091e24B361f0E519e2f7aD07a78995d",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "convertMultiple(address[],address[])":
            return self.parse_convert_multiple(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_convert_multiple(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # ignore everything after initial contract call
        return InterpretedTransactionGroup([transactions[0]])


class ViperSwapLiquidityEditor(UniswapDexEditor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Uniswap Router v2 Contract
        "0xf012702a5f0e54015362cBCA26a26fc90AA832a3",
        # HRC20 ViperPit (xVIPER)
        "0xE064a68994e9380250CfEE3E8C0e2AC5C0924548",
    ]
    XVIPER_HRC20_ADDRESS = "0xE064a68994e9380250CfEE3E8C0e2AC5C0924548"
    VIPER_HRC20_ADDRESS = "0xEa589E93Ff18b1a1F1e9BaC7EF3E86Ab62addc79"
    _HANDLERS = {
        # enter viperpit
        "enter(uint256)": "parse_enter",
        # exit viperpit
        "leave(uint256)": "parse_leave",
        **UniswapDexEditor._HANDLERS,
    }

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def parse_enter(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # VIPER -> xVIPER
        root_tx = transactions[0]

        o, i = self.get_pair_by_address(
            transactions, self.VIPER_HRC20_ADDRESS, self.XVIPER_HRC20_ADDRESS
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])

    def parse_leave(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # xVIPER -> VIPER
        root_tx = transactions[0]

        o, i = self.get_pair_by_address(
            transactions, self.XVIPER_HRC20_ADDRESS, self.VIPER_HRC20_ADDRESS
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])
