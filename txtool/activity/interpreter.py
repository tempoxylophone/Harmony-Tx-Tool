from abc import ABC
from typing import List, Dict, NewType
from decimal import Decimal
import copy

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
        lp_position_size = liquidity_received_tx.got_amount / 3

        for i in range(3):
            # copy original token transfer tx, give 3 transfer tx
            # where LP position is 1/3rd of full position
            d = copy.deepcopy(liquidity_received_tx)
            d.got_amount = lp_position_size
            d.coin_amount = lp_position_size

            results.append(d)
            results.append(transactions[i + 2])

        # write tx logs in order
        for i, x in enumerate(results):
            x.log_idx = i

        return results


EDITORS = [
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
