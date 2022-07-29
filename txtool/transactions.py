from __future__ import annotations
from typing import List, Optional, Union, Dict, Any
from enum import Enum
from eth_typing import HexStr
from txtool import contracts
from txtool.harmony import HarmonyToken, HarmonyAddress, HarmonyEVMTransaction, HarmonyAPI


class WalletAction(str, Enum):
    PAYMENT = 'payment'
    DEPOSIT = 'deposit'
    DONATION = 'donation'
    WITHDRAWAL = 'withdraw'
    NULL = ''


class WalletActivity(HarmonyEVMTransaction):

    def __init__(
            self,
            wallet_address: Union[HarmonyAddress, str],
            tx_hash: HexStr,
            harmony_token: Optional[HarmonyToken] = None
    ):
        # get information about this tx
        super().__init__(wallet_address, tx_hash)

        # set custom token if it is given
        self.coinType = harmony_token or self.coinType
        self._reinterpret_action()

    @property
    def is_receiver(self) -> bool:
        return self.to_addr == self.account

    @property
    def is_sender(self) -> bool:
        return self.from_addr == self.account

    def _get_action(self) -> WalletAction:
        if self.is_receiver:
            return self._is_payment() and WalletAction.PAYMENT or WalletAction.DEPOSIT

        if self.is_sender:
            return self._is_donation() and WalletAction.DONATION or WalletAction.WITHDRAWAL

        # unknown
        return WalletAction.NULL

    def _reinterpret_action(self):
        self.action = self._get_action()

        if self.action == WalletAction.DEPOSIT:
            # this wall got some currency
            self.sentAmount = 0
            self.sentCurrencySymbol = ''
            self.gotAmount = self.coinAmount
            self.gotCurrencySymbol = self.coinType.symbol
        else:
            # this wallet sent some currency
            self.sentAmount = self.coinAmount
            self.sentCurrencySymbol = self.coinType.symbol
            self.gotAmount = 0
            self.gotCurrencySymbol = ''

    def _is_payment(self) -> bool:
        return self.result['from'] in contracts.payment_wallets

    def _is_donation(self) -> bool:
        return (
                bool(self.result['to']) and
                'Donation' in contracts.getAddressName(self.result['to'])
        )

    @classmethod
    def extract_all_wallet_activity_from_transaction(
            cls,
            wallet_address: str,
            tx_hash: Union[HexStr, str]
    ) -> List[WalletActivity]:
        root_tx = WalletActivity(wallet_address, HexStr(tx_hash))
        leaf_tx = WalletActivity._get_token_transfers(root_tx)
        return [
            root_tx,
            # token transfers will appear in sub-transactions
            *leaf_tx
        ]

    @staticmethod
    def _get_token_transfers(root_tx: WalletActivity) -> List[WalletActivity]:
        wallet = root_tx.account
        receipt = root_tx.receipt

        transfers = []
        for log in HarmonyAPI.get_tx_transfer_logs(receipt):
            from_addr = log['args']['from']
            to_addr = log['args']['to']

            if from_addr != wallet.eth and to_addr != wallet.eth:
                # some intermediate tx
                continue

            transfers.append(
                WalletActivity._create_token_tx_from_log(root_tx, log)
            )

        return transfers

    @staticmethod
    def _create_token_tx_from_log(root_tx: WalletActivity, log: Dict[str, Any]) -> WalletActivity:
        token = HarmonyToken.get_harmony_token_by_address(log['address'])
        value = token.get_value_from_wei(log['args']['value'])

        r = WalletActivity(root_tx.account, root_tx.txHash, token)

        # TODO: why are there both value and coinAmount variables?
        r.value = value
        r.coinAmount = value
        r.event = log['event']
        r.is_token_transfer = r.event == "Transfer"

        # logs can be different from root transaction - must set them here
        r.to_addr = HarmonyAddress.get_harmony_address(log['args']['to'])
        r.from_addr = HarmonyAddress.get_harmony_address(log['args']['from'])
        r._reinterpret_action()

        return r

    def __str__(self) -> str:
        return "tx: {0} --[{1} {2}]--> {3} ({4})".format(
            self.from_addr.eth,
            self.value,
            self.coinType.symbol,
            self.to_addr.eth,
            self.txHash
        )
