from __future__ import annotations
from typing import List, Optional, Union
import contracts
from koinly_interpreter import KoinlyInterpreter
from harmony import HarmonyToken, HarmonyAddress, HarmonyEVMTransaction, HarmonyAPI


class WalletActivity(HarmonyEVMTransaction):

    @classmethod
    def extract_all_wallet_activity_from_transaction(cls, wallet_address: str, tx_hash: hex) -> List[WalletActivity]:
        base_tx_obj = WalletActivity(wallet_address, tx_hash)
        token_tx_objs = WalletActivity.get_token_activity_from_wallet_activity(base_tx_obj)
        return [base_tx_obj, *token_tx_objs]

    def __init__(
            self,
            wallet_address: Union[HarmonyAddress, str],
            tx_hash: hex,
            harmony_token: Optional[HarmonyToken] = None
    ):
        # get information about this tx
        super().__init__(wallet_address, tx_hash)

        # set custom token if it is given
        self.coinType = harmony_token or self.coinType

        # TODO: change all this, it's confusing
        self.depositEvent = 'payment' if self.is_payment() else 'deposit'
        self.withdrawalEvent = 'donation' if self.is_donation() else 'withdraw'

        if self.to_addr == self.account and self.value > 0:
            self.action = self.depositEvent
            self.address = HarmonyAddress.get_harmony_address(self.result['from'])

        if self.from_addr == self.account and self.value > 0:
            self.action = self.withdrawalEvent
            self.address = HarmonyAddress.get_harmony_address(self.result['to'])

        self.sentAmount = 0
        self.sentCurrency = None
        self.gotAmount = 0
        self.gotCurrency = None

        self.reinterpret_action()

    def reinterpret_action(self):
        if self.action == 'deposit':
            self.sentAmount = 0
            self.sentCurrency = None
            self.gotAmount = self.coinAmount
            self.gotCurrency = self.coinType.symbol
        else:
            self.sentAmount = self.coinAmount
            self.sentCurrency = self.coinType.symbol
            self.gotAmount = 0
            self.gotCurrency = None

    def is_payment(self) -> bool:
        return self.result['from'] in contracts.payment_wallets

    def is_donation(self) -> bool:
        return (
                self.result['to'] is not None and
                'Donation' in contracts.getAddressName(self.result['to'])
        )

    def get_koinly_description(self) -> str:
        # TODO: FIX
        if "Withdrawal to" not in self.action:
            return self.action
        else:
            return ""

    def get_koinly_label(self) -> str:
        if (
                self.sentAmount == 0 and self.sentCurrency == HarmonyToken.native_token().symbol and
                self.gotAmount == 0 and not bool(self.gotCurrency)
        ):
            return "cost"

        return ''

    def to_csv_row(self, use_one_address: bool) -> str:
        address_format = use_one_address and HarmonyAddress.FORMAT_ONE or HarmonyAddress.FORMAT_ETH
        return ','.join(
            (
                # time of transaction
                KoinlyInterpreter.parse_utc_ts(self.timestamp),

                # token sent in this tx (outgoing)
                str(self.sentAmount or ''),
                self.sentCurrency or '',

                # token received in this tx (incoming)
                str(self.gotAmount or ''),
                self.gotCurrency or '',

                # gas
                str(self.tx_fee_in_native_token),
                HarmonyToken.NATIVE_TOKEN_SYMBOL,

                # fiat conversion
                str(self.get_fiat_value()),
                self.fiatType,

                # description
                self.get_koinly_label(),
                self.get_koinly_description(),

                # transaction hash
                self.txHash,
                self.get_tx_function_signature(),

                # transfer information
                self.to_addr.get_address_str(address_format),
                self.from_addr.get_address_str(address_format),
                self.explorer_url,
                '\n'
            )
        )

    @staticmethod
    def get_token_activity_from_wallet_activity(wallet_activity_instance: WalletActivity) -> List[WalletActivity]:
        return WalletActivity._extract_token_transactions(
            wallet_activity_instance.txHash,
            wallet_activity_instance.account,
            wallet_activity_instance.receipt,
            wallet_activity_instance.depositEvent,
            wallet_activity_instance.withdrawalEvent
        )

    @staticmethod
    def _extract_token_transactions(txn, account_address: HarmonyAddress, receipt, depositEvent, withdrawalEvent):
        transfers = []
        for log in HarmonyAPI.get_tx_transfer_logs(receipt):
            if log['args']['from'] == account_address.eth:
                event = withdrawalEvent
                otherAddress = HarmonyAddress.get_harmony_address(log['args']['to'])
            elif log['args']['to'] == account_address.eth:
                event = depositEvent
                otherAddress = HarmonyAddress.get_harmony_address(log['args']['from'])
            else:
                continue

            token = HarmonyToken.get_harmony_token_by_address(log['address'])
            value = token.get_value_from_wei(log['args']['value'])

            r = WalletActivity(account_address, txn, token)
            r.action = event
            r.address = otherAddress
            r.value = value
            r.coinAmount = value
            r.reinterpret_action()

            transfers.append(r)

        return transfers
