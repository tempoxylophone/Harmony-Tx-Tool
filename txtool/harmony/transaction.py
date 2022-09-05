from __future__ import annotations
from datetime import datetime
from typing import Optional, List

from web3.types import TxReceipt, HexStr

from .api import HarmonyAPI
from .abc import Transaction
from .contract import HarmonyEVMSmartContract
from .address import HarmonyAddress, BadAddressException
from .token import Token, HarmonyToken, HarmonyNFT
from .signature import get_function_name_by_signature


class HarmonyEVMTransaction(Transaction):  # pylint: disable=R0902
    EXPLORER_TX_URL = "https://explorer.harmony.one/tx/{0}"

    def __init__(self, account: HarmonyAddress, tx_hash: HexStr):
        super().__init__(account, tx_hash)

        # get transaction data
        self.tx_data = HarmonyAPI.get_transaction(tx_hash)

        try:
            self.to_addr = HarmonyAddress.get_harmony_address(self.tx_data["to"])
        except BadAddressException as e:
            # bad address
            raise BadAddressException(
                f"Harmony EVM Transaction {tx_hash} had a null or invalid to address."
            ) from e

        self.from_addr = HarmonyAddress.get_harmony_address(self.tx_data["from"])

        # whether this is going IN or OUT depends on the perspective you take
        self.account = account

        # temporal data
        self.block = self.tx_data["blockNumber"]
        self.timestamp = HarmonyAPI.get_timestamp(self.block)
        self.block_date = datetime.fromtimestamp(self.timestamp)

        # event data
        self.action = ""
        self.event = ""
        self.is_token_transfer = False

        # function argument data
        self.contract_pointer = (
            HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(
                self.tx_data["to"]
            )
        )

        self.tx_payload = self.contract_pointer.decode_input(self.tx_data["input"])
        # currency data
        self.coin_amount = HarmonyAPI.get_coin_amount_from_tx_data(self.tx_data)

        # assume it is ONE unless otherwise specified, inheritors of this class can change
        # this based data relevant to what they do
        self.coin_type: Token = HarmonyToken.get_native_token()
        self.tx_fee_in_native_token = HarmonyAPI.get_tx_fee_from_tx_data(self.tx_data)

        # (placeholder values)
        self.sent_currency: Optional[Token] = None
        self.got_currency: Optional[Token] = None

        # position of transaction in logs
        self.log_idx = 0
        self.status = self.receipt['status']

    def get_relevant_tokens(self) -> List[HarmonyToken]:
        coins = {
            self.coin_type,
            self.got_currency,
            self.sent_currency,
            HarmonyToken.get_native_token(),
        } - {None}
        coins = list(coins)  # type: ignore
        return [
            x
            for x in coins
            if x and isinstance(x, HarmonyToken) and x.__class__ == HarmonyToken
        ]

    @property
    def did_fail(self) -> bool:
        return self.status == 0

    @property
    def receipt(self) -> TxReceipt:
        return HarmonyAPI.get_tx_receipt(self.tx_hash)

    @property
    def explorer_url(self) -> str:
        return self.EXPLORER_TX_URL.format(self.tx_hash)

    @property
    def method(self) -> str:
        return self.get_tx_function_signature()

    @property
    def method_for_csv_export(self) -> str:
        # escape and strip class name in python to string
        # need double quotes to prevent commas from next cell
        return '"{0}"'.format(self.get_tx_function_signature())

    @property
    def got_currency_symbol(self) -> str:
        return self.got_currency.symbol if self.got_currency else ""

    @property
    def got_currency_is_nft(self) -> bool:
        return isinstance(self.got_currency, HarmonyNFT)

    @property
    def got_currency_is_lp_token(self) -> bool:
        return self.got_currency.is_lp_token if self.got_currency else False

    @property
    def sent_currency_symbol(self) -> str:
        return self.sent_currency.symbol if self.sent_currency else ""

    @property
    def sent_currency_is_lp_token(self) -> bool:
        return self.sent_currency.is_lp_token if self.sent_currency else False

    @property
    def sent_currency_is_nft(self) -> bool:
        return isinstance(self.sent_currency, HarmonyNFT)

    @property
    def coin_type_symbol(self) -> str:
        return self.coin_type.symbol if self.coin_type else ""

    @property
    def from_addr_str(self) -> str:
        return self.from_addr.eth

    @property
    def to_addr_str(self) -> str:
        return self.to_addr.eth

    def get_tx_function_signature(self) -> str:
        decode_successful, function_info = self.tx_payload
        if decode_successful and function_info:
            f, _ = function_info

            # got function name from ABI
            return "{0}".format(str(f)[1:-1].split(" ")[1])

        # no luck trying to decode with an ABI... try to look up the
        # function signature in a database of known signatures
        input_data = self.tx_data["input"]

        # first 4 bytes of input (always 8 hex digits with 2 for '0x' prefix)
        func_signature = input_data[:10]

        return get_function_name_by_signature(func_signature)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HarmonyEVMTransaction):
            return False

        # two transactions are considered equal if they are of the same
        # parent hash and are of the same position on the logs
        return self.tx_hash == other.tx_hash and self.log_idx == other.log_idx

    def __hash__(self) -> int:
        return hash(f"{self.tx_hash}-{self.log_idx}")
