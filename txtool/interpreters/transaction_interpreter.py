from abc import ABC
from typing import List, Dict
from decimal import Decimal
from txtool.harmony import (
    HarmonyEVMSmartContract,
    HarmonyAddress,
    HarmonyToken,
    HarmonyEVMTransaction,
)


class Editor(ABC):
    CONTRACTS: Dict[HarmonyAddress, HarmonyEVMSmartContract] = {}

    def __init__(self, contract_addresses: List[str]):
        for contract_address in contract_addresses:
            smart_contract = (
                HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(
                    contract_address
                )
            )
            self.CONTRACTS[smart_contract.address] = smart_contract

    def should_interpret(self, transactions: List[HarmonyEVMTransaction]) -> bool:
        # expects list of transactions that were extracted from base tx activity
        root_tx = transactions[0]
        return root_tx.to_addr in self.CONTRACTS

    def interpret(
        self, transactions: List[HarmonyEVMTransaction]
    ) -> List[HarmonyEVMTransaction]:
        raise NotImplementedError


class TranquilFinanceEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Unitroller
        "0x6a82A17B48EF6be278BBC56138F35d04594587E3",
    ]

    def __init__(self):
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[HarmonyEVMTransaction]
    ) -> List[HarmonyEVMTransaction]:
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


EDITORS = [
    TranquilFinanceEditor(),
]


def interpret_multi_transaction(transactions: List[HarmonyEVMTransaction]):
    for t in EDITORS:
        # try all interpreters, if find a relevant one, interpret the txs
        if t.should_interpret(transactions):
            return t.interpret(transactions)

    return transactions
