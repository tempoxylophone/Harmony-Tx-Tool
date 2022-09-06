from __future__ import annotations
from typing import List, Optional, Union, Dict
from enum import Enum
from decimal import Decimal
from copy import deepcopy

from eth_typing import HexStr
from web3.types import EventData

from txtool.dfk.constants import HARMONY_TOKEN_ADDRESS_MAP, DFK_PAYMENT_WALLET_ADDRESSES
from txtool.utils import MAIN_LOGGER

from .token import HarmonyToken, Token, HarmonyNFT, HarmonyNFTCollection
from .api import HarmonyAPI
from .address import HarmonyAddress
from .transaction import HarmonyEVMTransaction


class WalletAction(str, Enum):
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    DONATION = "donation"
    WITHDRAWAL = "withdraw"
    NULL = ""


class WalletActivity(HarmonyEVMTransaction):  # pylint: disable=R0902
    def __init__(
        self,
        account: HarmonyAddress,
        tx_hash: HexStr,
        harmony_token: Optional[Token] = None,
    ):
        # get information about this tx
        super().__init__(account, tx_hash)

        self.is_nft_transfer = False

        # set custom token if it is given
        self.coin_type = harmony_token or self.coin_type
        self.reinterpret_action()

    @property
    def is_receiver(self) -> bool:
        return bool(self.to_addr == self.account)

    @property
    def is_sender(self) -> bool:
        return bool(self.from_addr == self.account)

    @property
    def is_trade(self) -> bool:
        return bool(
            self.got_amount > 0
            and self.sent_amount > 0
            and self.got_currency
            and self.sent_currency
            and self.got_currency != self.sent_currency
        )

    @property
    def should_include_in_csv_export(self) -> bool:
        # maybe better idea to pass a function to csv_creator where
        # you can define the properties that would cause a tx to be
        # omitted from export...

        # do not include failed / reverted transactions
        return not self.did_fail

    def _get_action(self) -> WalletAction:
        if self.is_receiver:
            return WalletAction.PAYMENT if self._is_payment() else WalletAction.DEPOSIT

        if self.is_sender:
            return (
                WalletAction.DONATION
                if self._is_donation()
                else WalletAction.WITHDRAWAL
            )

        # unknown
        return WalletAction.NULL

    def reinterpret_action(self) -> None:
        self.action = self._get_action()
        if self.action == WalletAction.DEPOSIT:
            # this wall got some currency
            self.sent_amount = Decimal(0)
            self.sent_currency = None
            self.got_amount = self.coin_amount
            self.got_currency = self.coin_type
        else:
            # this wallet sent some currency
            self.sent_amount = self.coin_amount
            self.sent_currency = self.coin_type
            self.got_amount = Decimal(0)
            self.got_currency = None

    def _is_payment(self) -> bool:
        return self.from_addr.eth in DFK_PAYMENT_WALLET_ADDRESSES

    def _is_donation(self) -> bool:
        return bool(self.to_addr) and "Donation" in HARMONY_TOKEN_ADDRESS_MAP.get(
            self.to_addr.eth, ""
        )

    @classmethod
    def extract_all_wallet_activity_from_transaction(
        cls,
        account: HarmonyAddress,
        tx_hash: Union[HexStr, str],
    ) -> List[WalletActivity]:
        root_tx = WalletActivity(account, HexStr(tx_hash))
        leaf_tx = WalletActivity._get_token_transfers(root_tx)
        nft_tx = WalletActivity._get_nft_transfers(root_tx)
        return [root_tx, *leaf_tx, *nft_tx]

    @staticmethod
    def _get_token_transfers(root_tx: WalletActivity) -> List[WalletActivity]:
        receipt = root_tx.receipt

        transfers: List[WalletActivity] = []
        logs = list(HarmonyAPI.get_tx_transfer_logs(receipt))

        for i, log in enumerate(logs, start=1):
            MAIN_LOGGER.info("\tExtracting sub-tx %s/%s...", i, len(logs))
            token_tx = WalletActivity._create_token_tx_from_log(root_tx, log)
            transfers.append(token_tx)

        return transfers

    @staticmethod
    def _get_nft_transfers(root_tx: WalletActivity) -> List[WalletActivity]:
        receipt = root_tx.receipt

        nft_transfer_logs = list(HarmonyAPI.get_tx_transfer_logs_nft(receipt))

        results = []
        if nft_transfer_logs:
            nft_collection_address = root_tx.to_addr.eth
            nft_collection = HarmonyNFTCollection(nft_collection_address)

            spent_per_mint = root_tx.coin_amount / len(nft_transfer_logs)

            for i, log in enumerate(nft_transfer_logs, start=1):
                MAIN_LOGGER.info(
                    "\tExtracting NFT tx %s/%s...", i, len(nft_transfer_logs)
                )
                results.append(
                    WalletActivity._create_nft_tx_from_log(
                        root_tx, log, nft_collection, spent_per_mint
                    )
                )

            # erase sent amount
            root_tx.sent_amount = Decimal(0)
            root_tx.coin_amount = Decimal(0)
            root_tx.got_amount = Decimal(0)

        return results

    @staticmethod
    def _create_token_tx_from_log(
        root_tx: WalletActivity, log: EventData
    ) -> WalletActivity:
        token = HarmonyToken.get_harmony_token_by_address(log["address"])
        value = token.get_value_from_wei(log["args"]["value"])

        r = WalletActivity(root_tx.account, root_tx.tx_hash, token)
        r.log_idx = log["logIndex"]
        r.coin_amount = value
        r.event = log["event"]
        r.is_token_transfer = r.event == "Transfer"
        r.is_nft_transfer = False
        r.tx_fee_in_native_token = Decimal(0)

        # logs can be different from root transaction - must set them here
        r.to_addr = HarmonyToken.get_address_and_set_token(log["args"]["to"])
        r.from_addr = HarmonyToken.get_address_and_set_token(log["args"]["from"])
        r.reinterpret_action()

        return r

    @staticmethod
    def _create_nft_tx_from_log(
        root_tx: WalletActivity,
        log: EventData,
        collection: HarmonyNFTCollection,
        initial_price_in_one: Decimal,
    ) -> WalletActivity:
        # create NFT instance
        token_id = log["args"]["tokenId"]
        token = HarmonyNFT.create_nft(token_id, collection)
        token.add_event(root_tx.tx_hash, initial_price_in_one)

        r = WalletActivity(root_tx.account, root_tx.tx_hash, token)
        r.log_idx = log["logIndex"]

        # x ONE -> 1 NFT
        r.got_amount = Decimal(1)
        r.got_currency = token
        r.sent_amount = initial_price_in_one
        r.sent_currency = token.get_native_token()
        r.tx_fee_in_native_token = Decimal(0)

        r.event = log["event"]
        r.is_token_transfer = False
        r.is_nft_transfer = True

        # logs can be different from root transaction - must set them here
        r.to_addr = HarmonyToken.get_address_and_set_token(log["args"]["to"])

        # usually this will be from 0x, but for book-keeping purposes, set it
        # to the ERC721 contract
        r.from_addr = root_tx.to_addr

        return r

    def __copy__(self) -> WalletActivity:
        new_tx = WalletActivity(self.account, self.tx_hash, self.coin_type)
        new_tx.__dict__.update(self.__dict__)
        return new_tx

    def __deepcopy__(self, memo: Dict) -> WalletActivity:
        self_module: str = self.__class__.__module__.rsplit(".", 1)[0]

        # create a copy of this transaction, set all important fields
        wallet_copy = WalletActivity(self.account, self.tx_hash, self.coin_type)
        memo[id(self)] = wallet_copy

        for attr_name, attr in self.__dict__.items():
            cls_module: str = attr.__class__.__module__.rsplit(".", 1)[0]
            v = attr
            if cls_module != self_module:
                # actually copy other stuff
                v = deepcopy(attr)
            setattr(wallet_copy, attr_name, v)

        return wallet_copy

    def __str__(self) -> str:  # pragma: no cover
        if self.sent_currency and self.got_currency:
            # this is a trade
            return "tx: {0} -- [{1} {2}] trade for [{3} {4}] --> {5} ({6}) - log idx = {7}".format(
                self.from_addr.eth,
                self.sent_amount,
                self.sent_currency_symbol,
                self.got_amount,
                self.got_currency_symbol,
                self.to_addr.eth,
                self.tx_hash,
                self.log_idx,
            )

        if self.is_sender:
            sign = "-"
        elif self.is_receiver:
            sign = "+"
        else:
            sign = ""

        nft_indicator = ""
        nft_price = ""

        if isinstance(self.coin_type, HarmonyNFT):
            nft_indicator = " [NFT Transfer]"
            nft_price = f" - latest price = {self.coin_type.latest_price_in_one} ONE"

        return "tx: {0} --[{1}{2} {3}]--> {4} ({5}) - log idx = {6}{7}{8}".format(
            self.from_addr.eth,
            sign,
            self.coin_amount,
            self.coin_type_symbol or "(NULL COIN TYPE)",
            self.to_addr.eth,
            self.tx_hash,
            self.log_idx,
            nft_indicator,
            nft_price,
        )
