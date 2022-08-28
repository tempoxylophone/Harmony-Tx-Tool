from abc import ABC, abstractmethod
from typing import List, Dict, NewType

from txtool.harmony import (
    HarmonyEVMSmartContract,
    HarmonyAddress,
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

    @abstractmethod
    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        raise NotImplementedError  # pragma: no cover
