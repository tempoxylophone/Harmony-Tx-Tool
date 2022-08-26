from abc import ABC
from typing import List, Dict, NewType
from decimal import Decimal
from copy import deepcopy

from txtool.harmony import (
    HarmonyEVMSmartContract,
    HarmonyAddress,
    HarmonyToken,
    WalletActivity,
)

InterpretedTransactionGroup = NewType(
    "InterpretedTransactionGroup", List[WalletActivity]
)


class Editor(ABC):
    def __init__(self, contract_addresses: List[str]):
        self.contracts: Dict[HarmonyAddress, HarmonyEVMSmartContract] = {}

        for contract_address in contract_addresses:
            smart_contract = (
                HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(
                    contract_address
                )
            )
            self.contracts[smart_contract.address] = smart_contract

    def should_interpret(self, transactions: List[WalletActivity]) -> bool:
        # expects list of transactions that were extracted from base tx activity
        root_tx = transactions[0]
        return root_tx.to_addr in self.contracts

    def interpret(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
        raise NotImplementedError  # pragma: no cover


class TranquilFinanceEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Unitroller
        "0x6a82A17B48EF6be278BBC56138F35d04594587E3",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
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

            return [
                # the cost transaction
                transactions[0],
                # all deposits from TRANQ rewards
                reward_tx,
            ]

        return transactions


class Curve3PoolLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        "0xC5cfaDA84E902aD92DD40194f0883ad49639b023",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
        if len(transactions) != 5:
            return transactions

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
            return transactions

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

        return results


class ViperSwapClaimRewardsEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Viper Rewards Contract
        "0x7AbC67c8D4b248A38B0dc5756300630108Cb48b4",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
        if (
            0 < len(transactions) < 3
            and transactions[0].method == "claimRewards(uint256[])"
        ):
            return transactions

        plus_tx = [
            x
            for x in transactions
            if x.is_receiver and x.got_currency_symbol == "VIPER"
        ]
        minus_tx = [
            x for x in transactions if x.is_sender and x.got_currency_symbol == "VIPER"
        ]

        consolidated_tx = deepcopy(plus_tx[0])

        delta = Decimal(
            sum(x.got_amount for x in plus_tx) + sum(x.sent_amount for x in minus_tx)
        )
        consolidated_tx.coin_amount = delta
        consolidated_tx.got_amount = delta
        consolidated_tx.log_idx = 1

        return [
            # the cost transaction used to invoke contract
            transactions[0],
            # the consolidated VIPER reward TX
            consolidated_tx,
        ]


class ViperSwapXRewardsEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap ViperPit
        "0x08913d353091e24B361f0E519e2f7aD07a78995d",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
        if (
            len(transactions) < 2
            or transactions[0].method != "convertMultiple(address[],address[])"
        ):
            return transactions

        # ignore all other sub-transactions
        return [
            # the cost transaction used to invoke contract
            transactions[0],
        ]


class ViperSwapLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Uniswap Router v2 Contract
        "0xf012702a5f0e54015362cBCA26a26fc90AA832a3",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
        if len(transactions) > 4:
            return transactions

        initial_tx = transactions[0]
        if initial_tx.method == "removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)":
            return self.interpret_remove_liquidity(transactions)
        elif "addLiquidity" in initial_tx.method:
            return self.interpret_add_liquidity(transactions)

    def interpret_remove_liquidity(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
        # there is 1 send transaction that sends away VENOM-LP
        # there are 2 get transactions that give you the original pair positions
        # break up the send transaction into two even positions, so that we can 'trade'
        # for the original pair
        cost_tx = transactions[0]
        send_tx_1 = next(x for x in transactions if x.is_sender and x.sent_currency_symbol == "VENOM-LP")
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
            get_tx_2,
            send_tx_2,
            get_tx_1,
            send_tx_1
        ]

        for i, tx in enumerate(in_order_txs):
            tx.log_idx = i

        return in_order_txs

    def interpret_add_liquidity(self, transactions: List[WalletActivity]) -> List[WalletActivity]:
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
            return transactions

        got_tx_1 = got_txs[0]
        got_tx_2 = deepcopy(got_tx_1)
        amount = got_tx_1.coin_amount / 2

        # easier for Koinly to detect as exchange
        got_tx_1.coin_amount = amount
        got_tx_1.got_amount = amount
        got_tx_2.coin_amount = amount
        got_tx_2.got_amount = amount

        send_tx_1, send_tx_2 = send_txs

        tx_log = [
            got_tx_1,
            send_tx_1,
            got_tx_2,
            send_tx_2,
        ]

        if cost_tx:
            # add back the cost TX if it was found
            tx_log.insert(0, cost_tx)

        for i, t in enumerate(tx_log):
            t.log_idx = i

        return tx_log



EDITORS = [
    ViperSwapClaimRewardsEditor(),
    ViperSwapXRewardsEditor(),
    ViperSwapLiquidityEditor(),
    TranquilFinanceEditor(),
    Curve3PoolLiquidityEditor(),
]


def interpret_multi_transaction(
    transactions: List[WalletActivity],
) -> List[WalletActivity]:
    for t in EDITORS:
        # try all interpreters, if find a relevant one, interpret the txs
        if t.should_interpret(transactions):
            return t.interpret(transactions)

    return transactions


def get_interpreted_transaction_from_hash(
    tx_hash: str,
) -> InterpretedTransactionGroup:
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(tx_hash)
    return InterpretedTransactionGroup(interpret_multi_transaction(txs))
