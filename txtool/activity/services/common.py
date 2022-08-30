from typing import List, Dict, NewType, Tuple, Callable
from decimal import Decimal
from copy import deepcopy

from txtool.harmony import (
    HarmonyEVMSmartContract,
    HarmonyAddress,
    WalletActivity,
)

InterpretedTransactionGroup = NewType(
    "InterpretedTransactionGroup", List[WalletActivity]
)


class Editor:
    _HANDLERS: Dict[str, str] = {}

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

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method
        f: Callable[[List[WalletActivity]], InterpretedTransactionGroup] = (
            # give transactions to appropriate handler
            getattr(self, self._HANDLERS[root_method])
            if root_method in self._HANDLERS
            else
            # do nothing, just cast
            InterpretedTransactionGroup
        )
        return f(transactions)

    def consolidate_trade(
        self, give_tx: WalletActivity, get_tx: WalletActivity
    ) -> WalletActivity:
        # get coins moved to / from
        give_tx.sent_amount = give_tx.coin_amount
        give_tx.sent_currency = give_tx.coin_type
        get_tx.got_amount = get_tx.coin_amount
        get_tx.got_currency = get_tx.coin_type

        # use get TX has source of truth for monetary value
        # mutate get_tx
        get_tx.sent_amount = give_tx.sent_amount
        get_tx.sent_currency = give_tx.sent_currency
        get_tx.to_addr = give_tx.to_addr
        get_tx.from_addr = give_tx.from_addr

        return get_tx

    def zero_non_root_cost(
        self, transactions: List[WalletActivity]
    ) -> List[WalletActivity]:
        # mutate costs
        for tx in transactions[1:]:
            tx.tx_fee_in_native_token = Decimal(0)

        return transactions

    def get_root_tx_input(self, transactions: List[WalletActivity]) -> Dict:
        root_tx = transactions[0]
        _, payload = root_tx.tx_payload
        if payload is None:
            return {}

        _, args = payload
        return args

    def split_copy(
        self, transaction: WalletActivity, split_factor: int
    ) -> List[WalletActivity]:
        transaction.coin_amount = transaction.coin_amount / Decimal(split_factor)
        return [transaction, *[deepcopy(transaction) for _ in range(1, split_factor)]]

    def get_pair_by_address(
        self, transactions: List[WalletActivity], token_a: str, token_b: str
    ) -> Tuple[WalletActivity, WalletActivity]:
        tx_a = next(x for x in transactions[1:] if x.coin_type.address.eth == token_a)
        tx_b = next(x for x in transactions[1:] if x.coin_type.address.eth == token_b)
        return tx_a, tx_b
