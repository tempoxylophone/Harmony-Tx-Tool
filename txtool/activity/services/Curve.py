from typing import List

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class CurveUSDBTCETHLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        "0x76147c0C989670D106b57763a24410A2a22e335E",
        "0xF98450B5602fa59CC66e1379DFfB6FDDc724CfC4",
    ]
    _HANDLERS = {
        "deposit(uint256)": "parse_deposit",
        "withdraw(uint256)": "parse_withdraw",
        "add_liquidity(uint256[5],uint256)": "parse_add_liquidity",
    }
    HRC_20_CRV_USD_BTC_ETH_ADDRESS = "0x99E8eD28B97c7F1878776eD94fFC77CABFB9B726"
    HRC_20_CRV_USD_BTC_ETH_GAUGE_ADDRESS = "0xF98450B5602fa59CC66e1379DFfB6FDDc724CfC4"

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def parse_deposit(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        o, i = self.get_pair_by_address(
            transactions,
            self.HRC_20_CRV_USD_BTC_ETH_ADDRESS,
            self.HRC_20_CRV_USD_BTC_ETH_GAUGE_ADDRESS,
        )
        return InterpretedTransactionGroup(
            self.zero_non_root_cost([transactions[0], self.consolidate_trade(o, i)])
        )

    def parse_withdraw(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        o, i = self.get_pair_by_address(
            transactions,
            self.HRC_20_CRV_USD_BTC_ETH_GAUGE_ADDRESS,
            self.HRC_20_CRV_USD_BTC_ETH_ADDRESS,
        )

        # edit null address
        o.to_addr = transactions[0].to_addr

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([transactions[0], self.consolidate_trade(o, i)])
        )

    def parse_add_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        cost_tx = transactions[0]
        give_tx = next(x for x in transactions[1:] if x.is_sender)
        get_tx = next(x for x in transactions[1:] if x.is_receiver)

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([cost_tx, self.consolidate_trade(give_tx, get_tx)])
        )


class Curve3PoolLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Curve.fi DAI/USDC/USDT
        "0xC5cfaDA84E902aD92DD40194f0883ad49639b023",
        # Curve.fi 3CRV RewardGauge Deposit
        "0xbF7E49483881C76487b0989CD7d9A8239B20CA41",
    ]
    HRC_20_3CRV_ADDRESS = "0xC5cfaDA84E902aD92DD40194f0883ad49639b023"
    HRC_20_3CRV_GAUGE_ADDRESS = "0xbF7E49483881C76487b0989CD7d9A8239B20CA41"
    _HANDLERS = {
        "claim_rewards(address)": "parse_claim_rewards",
        "add_liquidity(uint256[3],uint256)": "parse_add_liquidity",
        "remove_liquidity(uint256,uint256[3])": "parse_remove_liquidity",
        "remove_liquidity_imbalance(uint256[3],uint256)": "parse_remove_liquidity_imbalance",
        "exchange(int128,int128,uint256,uint256)": "parse_exchange",
        "deposit(uint256)": "parse_deposit",
        "withdraw(uint256)": "parse_withdraw",
    }

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def parse_exchange(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        o = next(x for x in transactions[1:] if x.is_sender)
        i = next(x for x in transactions[1:] if x.is_receiver)
        return InterpretedTransactionGroup(
            self.zero_non_root_cost([transactions[0], self.consolidate_trade(o, i)])
        )

    def parse_claim_rewards(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [
                    transactions[0],
                    # remove intermediate txs
                    *[x for x in transactions[1:] if x.is_receiver],
                ]
            )
        )

    def parse_add_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) == 3:
            # (USDC/DAI/USDT) (one of these) -> 3CRV
            cost_tx = transactions[0]
            o = next(x for x in transactions[1:] if x.is_sender)
            i = next(x for x in transactions[1:] if x.is_receiver)
            return InterpretedTransactionGroup(
                self.zero_non_root_cost([cost_tx, self.consolidate_trade(o, i)])
            )

        if len(transactions) == 5:
            # USDC/DAI/USDT -> 3CRV
            liquidity_received_tx = transactions[-1]
            i_1, i_2, i_3 = self.split_copy(liquidity_received_tx, 3)
            o_1, o_2, o_3 = transactions[1:4]

            return InterpretedTransactionGroup(
                self.zero_non_root_cost(
                    [
                        transactions[0],
                        self.consolidate_trade(o_1, i_1),
                        self.consolidate_trade(o_2, i_2),
                        self.consolidate_trade(o_3, i_3),
                    ]
                )
            )

        # doesn't apply here
        return InterpretedTransactionGroup(transactions)

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
            self.zero_non_root_cost(
                [
                    transactions[0],
                    self.consolidate_trade(o_1, i_1),
                    self.consolidate_trade(o_2, i_2),
                    self.consolidate_trade(o_3, i_3),
                ]
            )
        )

    def parse_remove_liquidity_imbalance(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # remove all your LP position as 1 currency
        cost_tx = transactions[0]
        give_tx = next(x for x in transactions[1:] if x.is_sender)
        get_tx = next(x for x in transactions[1:] if x.is_receiver)
        return InterpretedTransactionGroup(
            self.zero_non_root_cost([cost_tx, self.consolidate_trade(give_tx, get_tx)])
        )

    def parse_deposit(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        o, i = self.get_pair_by_address(
            transactions, self.HRC_20_3CRV_ADDRESS, self.HRC_20_3CRV_GAUGE_ADDRESS
        )
        return InterpretedTransactionGroup(
            self.zero_non_root_cost([transactions[0], self.consolidate_trade(o, i)])
        )

    def parse_withdraw(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        o, i = self.get_pair_by_address(
            transactions, self.HRC_20_3CRV_GAUGE_ADDRESS, self.HRC_20_3CRV_ADDRESS
        )

        # edit null address
        o.to_addr = transactions[0].to_addr

        # give away 3CRV-gauge, get back 3CRV
        return InterpretedTransactionGroup(
            self.zero_non_root_cost([transactions[0], self.consolidate_trade(o, i)])
        )
