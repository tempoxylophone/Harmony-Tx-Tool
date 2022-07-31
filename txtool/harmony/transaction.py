from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import Union

from web3.types import TxReceipt, HexStr

from .api import HarmonyAPI
from .abc import Transaction
from .contract import HarmonyEVMSmartContract
from .address import HarmonyAddress
from .token import HarmonyToken, DexPriceManager


class HarmonyEVMTransaction(Transaction):  # pylint: disable=R0902
    EXPLORER_TX_URL = "https://explorer.harmony.one/tx/{0}"

    def __init__(self, account: Union[HarmonyAddress, str], tx_hash: HexStr):
        super().__init__(HarmonyAddress.get_harmony_address(account), tx_hash)

        # get transaction data
        tx_data = HarmonyAPI.get_transaction(tx_hash)
        self.to_addr = HarmonyAddress.get_harmony_address(tx_data["to"])
        self.from_addr = HarmonyAddress.get_harmony_address(tx_data["from"])

        # temporal data
        self.block = tx_data["blockNumber"]
        self.timestamp = HarmonyAPI.get_timestamp(self.block)
        self.block_date = date.fromtimestamp(self.timestamp)

        # event data
        self.action = ""
        self.event = ""
        self.is_token_transfer = False

        # function argument data
        self.contract_pointer = (
            HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(
                tx_data["to"]
            )
        )
        self.tx_payload = self.contract_pointer.decode_input(tx_data["input"])

        # currency data
        self.coin_amount = HarmonyAPI.get_coin_amount_from_tx_data(tx_data)

        # assume it is ONE unless otherwise specified, inheritors of this class can change
        # this based data relevant to what they do
        self.coin_type: HarmonyToken = HarmonyToken.get_native_token()
        self.tx_fee_in_native_token = HarmonyAPI.get_tx_fee_from_tx_data(tx_data)

    @property
    def receipt(self) -> TxReceipt:
        return HarmonyAPI.get_tx_receipt(self.tx_hash)

    @property
    def explorer_url(self):
        return self.EXPLORER_TX_URL.format(self.tx_hash)

    def get_token_price(self) -> Decimal:
        return DexPriceManager.get_price_of_token_at_block(self.coin_type, self.block)

    def get_fee_price(self) -> Decimal:
        return DexPriceManager.get_price_of_token_at_block(
            HarmonyToken.get_native_token(), self.block
        )

    def get_tx_function_signature(self) -> str:
        decode_successful, function_info = self.tx_payload
        if decode_successful and function_info:
            f, _ = function_info

            # escape and strip class name in python to string
            return "{0}".format(str(f)[1:-1].split(" ")[1])

        return ""
