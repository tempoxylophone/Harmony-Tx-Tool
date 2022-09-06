from typing import List

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup
from .dex import UniswapDexEditor, MasterChefDexEditor


class ViperSwapClaimRewardsEditor(MasterChefDexEditor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Viper Rewards Contract
        "0x7AbC67c8D4b248A38B0dc5756300630108Cb48b4",
    ]
    GOV_TOKEN_SYMBOL = "VIPER"
    LP_TOKEN_SYMBOL_PREFIX = "VENOM-LP"

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)


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

        trade_tx = self.consolidate_trade(o, i)
        trade_tx.to_addr = root_tx.to_addr
        trade_tx.from_addr = root_tx.from_addr

        return InterpretedTransactionGroup(self.zero_non_root_cost([root_tx, trade_tx]))

    def parse_leave(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # xVIPER -> VIPER
        root_tx = transactions[0]

        o, i = self.get_pair_by_address(
            transactions, self.XVIPER_HRC20_ADDRESS, self.VIPER_HRC20_ADDRESS
        )

        trade_tx = self.consolidate_trade(o, i)
        trade_tx.to_addr = root_tx.to_addr
        trade_tx.from_addr = root_tx.from_addr

        return InterpretedTransactionGroup(self.zero_non_root_cost([root_tx, trade_tx]))
