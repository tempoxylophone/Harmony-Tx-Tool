from typing import List
from decimal import Decimal
from copy import deepcopy

from txtool.harmony import (
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


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
            # add liquidity TX, not much to do
            if len(transactions) == 2:
                # only cost + deposit
                return InterpretedTransactionGroup(transactions)

            # add liquidity and claim rewards
            # everything after the first two is some kind of claim reward
            # when you enter an LP position you had already entered, when
            # you stake the position, you automatically claim rewards
            deposit_txs = transactions[:2]
            claim_txs = transactions[2:]
            net_claim_tx = self._consolidate_claims(claim_txs)
            return InterpretedTransactionGroup(
                [
                    *deposit_txs,
                    net_claim_tx,
                ]
            )

        if root_method in ("claimRewards(uint256[])", "claimReward(uint256)"):
            # claim rewards only
            cost_tx = transactions[0]
            net_claim_tx = self._consolidate_claims(transactions[1:])
            return InterpretedTransactionGroup([cost_tx, net_claim_tx])

        # unknown pattern
        return InterpretedTransactionGroup(transactions)

    def _consolidate_claims(
        self, claim_transactions: List[WalletActivity]
    ) -> WalletActivity:
        plus_tx = [
            x
            for x in claim_transactions
            if x.is_receiver and x.got_currency_symbol == "VIPER"
        ]
        minus_tx = [
            x
            for x in claim_transactions
            if x.is_sender and x.got_currency_symbol == "VIPER"
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
        if (
            len(transactions) < 2
            or transactions[0].method != "convertMultiple(address[],address[])"
        ):
            return InterpretedTransactionGroup(transactions)

        # ignore all other sub-transactions
        return InterpretedTransactionGroup(
            [
                # the cost transaction used to invoke contract
                transactions[0],
            ]
        )


class ViperSwapLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Uniswap Router v2 Contract
        "0xf012702a5f0e54015362cBCA26a26fc90AA832a3",
        # HRC20 ViperPit (xVIPER)
        "0xE064a68994e9380250CfEE3E8C0e2AC5C0924548",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) > 4:
            # unrecognized
            return InterpretedTransactionGroup(transactions)

        initial_tx = transactions[0]

        if "removeLiquidity" in initial_tx.method:
            # removal
            return self.interpret_remove_liquidity(transactions)

        if "addLiquidity" in initial_tx.method:
            # add
            return self.interpret_add_liquidity(transactions)

        if len(transactions) in (2, 3) and all(
            self._should_treat_as_trade(x) for x in transactions
        ):
            cost_tx = transactions[0] if len(transactions) == 3 else None

            # this is a trade
            give_tx = next(x for x in transactions[int(bool(cost_tx)) :] if x.is_sender)
            get_tx = next(
                x for x in transactions[int(bool(cost_tx)) :] if x.is_receiver
            )

            return InterpretedTransactionGroup(
                (cost_tx and [cost_tx] or [])
                + [self.consolidate_trade(give_tx, get_tx)]
            )

        # this editor is not relevant to this transaction group
        return InterpretedTransactionGroup(transactions)

    def _should_treat_as_trade(self, x: WalletActivity) -> bool:
        return (
            # standard uniswap style tx
            "swap" in x.method
            or
            # enter the viperpit (VIPER -> xVIPER)
            x.method == "enter(uint256)"
            or
            # leave the viperpit (xVIPER -> VIPER)
            x.method == "leave(uint256)"
        )

    def interpret_remove_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # there is 1 send transaction that sends away VENOM-LP
        # there are 2 get transactions that give you the original pair positions
        # break up the send transaction into two even positions, so that we can 'trade'
        # for the original pair
        cost_tx = transactions[0]

        send_tx_1 = next(
            x
            for x in transactions
            if x.is_sender and x.sent_currency_symbol == "VENOM-LP"
        )
        get_tx = [x for x in transactions if x.is_receiver]

        lp_amount = send_tx_1.coin_amount / 2
        send_tx_2 = deepcopy(send_tx_1)

        send_tx_1.coin_amount = lp_amount
        send_tx_1.sent_amount = lp_amount
        send_tx_2.coin_amount = lp_amount
        send_tx_2.sent_amount = lp_amount

        get_tx_1, get_tx_2 = get_tx

        in_order_txs = [
            cost_tx,
            self.consolidate_trade(send_tx_2, get_tx_2),
            self.consolidate_trade(send_tx_1, get_tx_1),
        ]

        return InterpretedTransactionGroup(in_order_txs)

    def interpret_add_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # there are 2 cases we must consider:
        # 1. you are adding Liquidity to a ONE/x LP and the first transaction
        # has a non-zero ONE amount - in this case, the tx signature
        # will be 'addLiquidityETH'
        # 2. you are adding Liquidity to a x/y LP (no ONE in pair) and the
        # first transaction is the cost - in this case, the tx signature
        # will be 'addLiquidity'
        send_txs = [x for x in transactions if x.is_sender]
        if len(send_txs) == 3:
            # x/y LP, remove the ONE transaction
            cost_tx = next(x for x in send_txs if x.sent_currency_symbol == "ONE")
            send_txs.remove(cost_tx)
        else:
            # ONE/x LP
            cost_tx = None

        got_txs = [x for x in transactions if x.is_receiver]

        if (
            len(got_txs) != 1
            or len(send_txs) != 2
            or got_txs[0].got_currency_symbol != "VENOM-LP"
        ):
            return InterpretedTransactionGroup(transactions)

        got_tx_1 = got_txs[0]
        got_tx_2 = deepcopy(got_tx_1)
        amount = got_tx_1.coin_amount / 2

        got_tx_1.coin_amount = amount
        got_tx_1.got_amount = amount
        got_tx_2.coin_amount = amount
        got_tx_2.got_amount = amount

        send_tx_1, send_tx_2 = send_txs

        tx_log = [
            self.consolidate_trade(send_tx_2, got_tx_2),
            self.consolidate_trade(send_tx_1, got_tx_1),
        ]

        if cost_tx:
            # add back the cost TX if it was found
            tx_log.insert(0, cost_tx)

        return InterpretedTransactionGroup(tx_log)
