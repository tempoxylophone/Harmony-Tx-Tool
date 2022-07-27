from __future__ import annotations
from typing import List, Optional, Union
import contracts
from koinly_interpreter import KoinlyInterpreter
from harmony import HarmonyToken, HarmonyAddress, HarmonyEVMTransaction, HarmonyAPI


class walletActivity(HarmonyEVMTransaction):

    @classmethod
    def extract_all_wallet_activity_from_transaction(cls, wallet_address: str, tx_hash: hex) -> List[walletActivity]:
        base_tx_obj = walletActivity(wallet_address, tx_hash)
        token_tx_objs = walletActivity.get_token_activity_from_wallet_activity(base_tx_obj)
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
        return ''

    def get_koinly_label(self) -> str:
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

                '\n'
            )
        )

    @staticmethod
    def get_token_activity_from_wallet_activity(wallet_activity_instance: walletActivity) -> List[walletActivity]:
        return walletActivity._extractTokenResults(
            wallet_activity_instance.txHash,
            wallet_activity_instance.account,
            wallet_activity_instance.receipt,
            wallet_activity_instance.depositEvent,
            wallet_activity_instance.withdrawalEvent
        )

    @staticmethod
    def _extractTokenResults(txn, account_address: HarmonyAddress, receipt, depositEvent, withdrawalEvent):
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

            non_native_token = HarmonyToken.get_harmony_token_by_address(log['address'])
            tokenValue = non_native_token.get_value_from_wei(log['args']['value'])

            r = walletActivity(account_address, txn, non_native_token)
            r.action = event
            r.address = otherAddress
            r.value = tokenValue
            r.coinAmount = tokenValue
            r.reinterpret_action()

            transfers.append(r)

        return transfers


# Records for Capital Gains
class TavernTransaction:
    def __init__(self, txHash, itemType, itemID, event, timestamp, coinType, coinCost=0, fiatType='usd', fiatAmount=0,
                 seller='', fiatFeeValue=0):
        self.txHash = txHash
        # hero or pet or land
        self.itemType = itemType
        self.itemID = itemID
        # purchase/sale/hire/summon/crystal/perished/incubate/crack/pvpfee/pvpreward
        self.event = event
        self.timestamp = timestamp
        self.coinType = coinType
        self.coinCost = coinCost
        self.fiatType = fiatType
        self.fiatAmount = fiatAmount
        self.fiatFeeValue = fiatFeeValue
        # Wallet address of seller in transaction or other metadata for non sale records
        self.seller = seller


class TraderTransaction:
    def __init__(self, txHash, timestamp, swapType, receiveType, swapAmount=0, receiveAmount=0, fiatType='usd',
                 fiatSwapValue=0, fiatReceiveValue=0, fiatFeeValue=0):
        self.txHash = txHash
        # timestamp of block when this transaction was done
        self.timestamp = timestamp
        # token type that was traded away
        self.swapType = swapType
        self.swapAmount = swapAmount
        # token type that was received
        self.receiveType = receiveType
        self.receiveAmount = receiveAmount
        # fiat equivalents of token values at the time
        self.fiatType = fiatType
        self.fiatSwapValue = fiatSwapValue
        self.fiatReceiveValue = fiatReceiveValue
        self.fiatFeeValue = fiatFeeValue
        # These are tracking fields for tracking amounts that have been allocated for tax records during mapping
        self.swapAmountNotAccounted = swapAmount
        self.receiveAmountNotAccounted = receiveAmount


class LiquidityTransaction:
    def __init__(self, txHash, timestamp, action, poolAddress, poolAmount, coin1Type, coin1Amount, coin2Type,
                 coin2Amount, fiatType='usd', coin1FiatValue=0, coin2FiatValue=0, fiatFeeValue=0):
        self.txHash = txHash
        # timestamp of block when transaction was done
        self.timestamp = timestamp
        # deposit tokens or withdraw (LP tokens)
        self.action = action
        # which liquidity pool
        self.poolAddress = poolAddress
        # number of LP tokens
        self.poolAmount = poolAmount
        # coin 1 should be the native token (jewel/crystal)
        self.coin1Type = coin1Type
        self.coin1Amount = coin1Amount
        self.coin2Type = coin2Type
        self.coin2Amount = coin2Amount
        self.fiatType = fiatType
        self.coin1FiatValue = coin1FiatValue
        self.coin2FiatValue = coin2FiatValue
        self.fiatFeeValue = fiatFeeValue
        # Tracking for mapping amounts to tax records
        self.amountNotAccounted = poolAmount


# Records for Income
class GardenerTransaction:
    def __init__(self, txHash, timestamp, event, coinType, coinAmount=0, fiatType='usd', fiatValue=0, fiatFeeValue=0):
        self.txHash = txHash
        self.timestamp = timestamp
        # deposit, withdraw, staking-reward, staking-reward-locked
        self.event = event
        self.coinType = coinType
        self.coinAmount = coinAmount
        self.fiatType = fiatType
        self.fiatValue = fiatValue
        self.fiatFeeValue = fiatFeeValue
        self.amountNotAccounted = coinAmount


class BankTransaction:
    def __init__(self, txHash, timestamp, action, xRate, coinType, coinAmount=0, fiatType='usd', fiatValue=0,
                 fiatFeeValue=0):
        self.txHash = txHash
        self.timestamp = timestamp
        # deposit or withdraw
        self.action = action
        # Bank xJewel/interest multiplier at the time
        self.xRate = xRate
        self.coinType = coinType
        self.coinAmount = coinAmount
        self.fiatType = fiatType
        self.fiatValue = fiatValue
        self.fiatFeeValue = fiatFeeValue
        # Just for tracking amounts that have been allocated to tax records during mapping
        self.amountNotAccounted = coinAmount / xRate


class AirdropTransaction:
    def __init__(self, txHash, timestamp, address, tokenReceived, tokenAmount=0, fiatType='usd', fiatValue=0,
                 fiatFeeValue=0):
        self.txHash = txHash
        self.timestamp = timestamp
        self.address = address
        self.tokenReceived = tokenReceived
        self.tokenAmount = tokenAmount
        self.fiatType = fiatType
        self.fiatValue = fiatValue
        self.fiatFeeValue = fiatFeeValue
        # Just for tracking amounts that have been allocated to tax records during mapping
        self.amountNotAccounted = tokenAmount


class QuestTransaction:
    def __init__(self, txHash, timestamp, rewardType, rewardAmount=0, fiatType='usd', fiatValue=0, fiatFeeValue=0):
        self.txHash = txHash
        self.timestamp = timestamp
        # what did we get on the quest, address of it
        self.rewardType = rewardType
        self.rewardAmount = rewardAmount
        self.fiatType = fiatType
        self.fiatValue = fiatValue
        self.fiatFeeValue = fiatFeeValue
        self.amountNotAccounted = rewardAmount


class AlchemistTransaction:
    def __init__(self, txHash, timestamp, craftingType, craftingAmount=0, fiatType='usd', fiatValue=0, craftingCosts=0,
                 costsFiatValue=0, fiatFeeValue=0):
        self.txHash = txHash
        self.timestamp = timestamp
        # what did we craft with alchemist, address of it
        self.craftingType = craftingType
        # how many were crafted
        self.craftingAmount = craftingAmount
        self.fiatType = fiatType
        self.fiatValue = fiatValue
        self.fiatFeeValue = fiatFeeValue
        # list of ingredients and qty burned
        self.craftingCosts = craftingCosts
        # fiat value of those ingredients at the time
        self.costsFiatValue = costsFiatValue


class LendingTransaction:
    def __init__(self, txHash, timestamp, event, address, coinType, coinAmount=0, fiatType='usd', fiatValue=0,
                 fiatFeeValue=0):
        self.txHash = txHash
        self.timestamp = timestamp
        # lend/redeem/borrow/repay/liquidate
        self.event = event
        self.address = address
        self.coinType = coinType
        self.coinAmount = coinAmount
        self.fiatType = fiatType
        self.fiatValue = fiatValue
        self.fiatFeeValue = fiatFeeValue
        self.amountNotAccounted = coinAmount
