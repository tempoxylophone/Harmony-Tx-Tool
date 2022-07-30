from __future__ import annotations
from typing import List, Optional, Union, Dict, Any
from enum import Enum
from eth_typing import HexStr
from txtool.harmony import (
    HarmonyToken,
    HarmonyAddress,
    HarmonyEVMTransaction,
    HarmonyAPI,
)

from txtool.dfk.constants import HARMONY_TOKEN_ADDRESS_MAP, DFK_PAYMENT_WALLET_ADDRESSES
from txtool.utils import MAIN_LOGGER


class WalletAction(str, Enum):
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    DONATION = "donation"
    WITHDRAWAL = "withdraw"
    NULL = ""


class WalletActivity(HarmonyEVMTransaction):  # pylint: disable=R0902
    def __init__(
        self,
        wallet_address: Union[HarmonyAddress, str],
        tx_hash: HexStr,
        harmony_token: Optional[HarmonyToken] = None,
    ):
        # get information about this tx
        super().__init__(wallet_address, tx_hash)

        # set custom token if it is given
        self.coin_type = harmony_token or self.coin_type
        self.reinterpret_action()

    @property
    def is_receiver(self) -> bool:
        return self.to_addr == self.account

    @property
    def is_sender(self) -> bool:
        return self.from_addr == self.account

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

    def reinterpret_action(self):
        self.action = self._get_action()

        if self.action == WalletAction.DEPOSIT:
            # this wall got some currency
            self.sent_amount = 0
            self.sent_amount = ""
            self.got_amount = self.coin_amount
            self.got_currency_symbol = self.coin_type.symbol
        else:
            # this wallet sent some currency
            self.sent_amount = self.coin_amount
            self.sent_currency_symbol = self.coin_type.symbol
            self.got_amount = 0
            self.got_currency_symbol = ""

    def _is_payment(self) -> bool:
        return self.result["from"] in DFK_PAYMENT_WALLET_ADDRESSES

    def _is_donation(self) -> bool:
        return bool(self.result["to"]) and "Donation" in HARMONY_TOKEN_ADDRESS_MAP.get(
            self.result["to"], ""
        )

    @classmethod
    def extract_all_wallet_activity_from_transaction(
        cls,
        wallet_address: str,
        tx_hash: Union[HexStr, str],
        exclude_intermediate_tx: Optional[bool] = True,
    ) -> List[WalletActivity]:
        root_tx = WalletActivity(wallet_address, HexStr(tx_hash))
        leaf_tx = WalletActivity._get_token_transfers(root_tx, exclude_intermediate_tx)
        return [
            root_tx,
            # token transfers will appear in sub-transactions
            *leaf_tx,
        ]

    @staticmethod
    def _get_token_transfers(
        root_tx: WalletActivity, exclude_intermediate_tx: Optional[bool] = True
    ) -> List[WalletActivity]:
        wallet = root_tx.account
        receipt = root_tx.receipt
        destination = root_tx.to_addr.eth

        transfers: List[WalletActivity] = []
        logs = list(HarmonyAPI.get_tx_transfer_logs(receipt))

        for i, log in enumerate(logs, start=1):
            from_addr = log["args"]["from"]
            to_addr = log["args"]["to"]

            MAIN_LOGGER.info("\tExtracting sub-tx %s/%s...", i, len(logs))

            if exclude_intermediate_tx and (
                wallet.eth not in (from_addr, to_addr) and destination != to_addr
            ):
                # some intermediate tx
                MAIN_LOGGER.info("\t\tSkipping intermediate transaction...")
                continue

            # in reverse order
            transfers.insert(0, WalletActivity._create_token_tx_from_log(root_tx, log))

        return transfers

    @staticmethod
    def _create_token_tx_from_log(
        root_tx: WalletActivity, log: Dict[str, Any]
    ) -> WalletActivity:
        token = HarmonyToken.get_harmony_token_by_address(log["address"])
        value = token.get_value_from_wei(log["args"]["value"])

        r = WalletActivity(root_tx.account, root_tx.tx_hash, token)

        r.coin_amount = value
        r.event = log["event"]
        r.is_token_transfer = r.event == "Transfer"

        # logs can be different from root transaction - must set them here
        r.to_addr = HarmonyAddress.get_harmony_address(log["args"]["to"])
        r.from_addr = HarmonyAddress.get_harmony_address(log["args"]["from"])
        r.reinterpret_action()

        return r

    def __str__(self) -> str:  # pragma: no cover
        return "tx: {0} --[{1} {2}]--> {3} ({4})".format(
            self.from_addr.eth,
            self.coin_amount,
            self.coin_type.symbol,
            self.to_addr.eth,
            self.tx_hash,
        )
