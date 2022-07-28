from __future__ import annotations
from typing import List, Optional, Union
from enum import Enum
import contracts
from koinly_interpreter import KoinlyInterpreter
from harmony import HarmonyToken, HarmonyAddress, HarmonyEVMTransaction, HarmonyAPI


class WalletAction(str, Enum):
    PAYMENT = 'payment'
    DEPOSIT = 'deposit'
    DONATION = 'donation'
    WITHDRAWAL = 'withdraw'


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
        self.sentAmount = 0
        self.sentCurrency = None
        self.gotAmount = 0
        self.gotCurrency = None

        self.reinterpret_action()

    def reinterpret_action(self):
        if not self.is_token_transfer:
            if self.to_addr == self.account and self.value > 0:
                self.action = self.is_payment() and WalletAction.PAYMENT or WalletAction.DEPOSIT
                self.from_addr = HarmonyAddress.get_harmony_address(self.result['from'])

            if self.from_addr == self.account and self.value > 0:
                self.action = self.is_donation() and WalletAction.DONATION or WalletAction.WITHDRAWAL
                self.to_addr = HarmonyAddress.get_harmony_address(self.result['to'])

        if self.action == WalletAction.DEPOSIT:
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
        if self.to_addr.belongs_to_smart_contract and not self.to_addr.belongs_to_token and self.value > 0 and self.sentCurrency:
            # wallet sent something to smart contract
            return f"sent {self.sentCurrency} to smart contract"

        if self.from_addr == self.account and self.value > 0 and self.gotCurrency and self.to_addr.belongs_to_smart_contract:
            return f"got {self.gotCurrency} from smart contract"

        return self.action

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
        )

    @staticmethod
    def _extract_token_transactions(txn: str, account_address: HarmonyAddress, receipt):
        transfers = []
        for log in HarmonyAPI.get_tx_transfer_logs(receipt):
            from_addr = log['args']['from']
            to_addr = log['args']['to']

            if from_addr != account_address.eth and to_addr != account_address.eth:
                # some intermediate tx
                continue

            token = HarmonyToken.get_harmony_token_by_address(log['address'])
            value = token.get_value_from_wei(log['args']['value'])

            r = WalletActivity(account_address, txn, token)
            r.value = value
            r.coinAmount = value
            r.event = log['event']
            r.is_token_transfer = r.event == "Transfer"
            r.reinterpret_action()
            r.to_addr = HarmonyAddress.get_harmony_address(to_addr)
            r.from_addr = HarmonyAddress.get_harmony_address(from_addr)

            transfers.append(r)

        return transfers

    def __str__(self) -> str:
        return "tx: {0} --[{1} {2}]--> {3} ({4})".format(
            self.from_addr.eth,
            self.value,
            self.coinType.symbol,
            self.to_addr.eth,
            self.txHash
        )
