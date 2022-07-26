from __future__ import annotations
import datetime
from typing import List
from web3 import Web3
from web3.logs import DISCARD
from pyharmony import pyharmony

import nets
import contracts
from contracts import HarmonyEVMSmartContract
from koinly_interpreter import KoinlyInterpreter


class HarmonyAddress:
    w3 = Web3(Web3.HTTPProvider(nets.hmy_web3))
    FORMAT_ETH = "eth"
    FORMAT_ONE = "one"
    bech32_hrp = "one"

    def __init__(self, address: str):
        self.addresses = {
            self.FORMAT_ETH: "",
            self.FORMAT_ONE: "",
        }

        if pyharmony.account.is_valid_address(address):
            # given a one address
            self.address_format = self.FORMAT_ONE
            self.addresses[self.FORMAT_ONE] = address
            self.addresses[self.FORMAT_ETH] = pyharmony.util.convert_one_to_hex(address)
        elif HarmonyAddress.w3.isAddress(address):
            # given an ethereum address
            self.address_format = self.FORMAT_ETH
            self.addresses[self.FORMAT_ETH] = address
            self.addresses[self.FORMAT_ONE] = self.convert_hex_to_one(address)
        else:
            raise ValueError("Bad address! Got: {0}".format(address))

    @staticmethod
    def convert_hex_to_one(hex_eth_address: str) -> str:
        p = bytearray.fromhex(
            # remove 0x prefix from ethereum address if necessary
            hex_eth_address[2:] if hex_eth_address.startswith("0x") else hex_eth_address
        )

        # encode to bech32 style "one" address
        return pyharmony.bech32.bech32_encode(
            HarmonyAddress.bech32_hrp,
            pyharmony.bech32.convertbits(p, 8, 5)
        )

    def get_address_str(self, address_format: str) -> str:
        return self.addresses[address_format]

    def get_eth_address(self) -> str:
        return self.get_address_str(self.FORMAT_ETH)

    def get_one_address(self) -> str:
        return self.get_address_str(self.FORMAT_ONE)

    def __str__(self) -> str:
        # default to eth address format
        return self.get_eth_address()


class HarmonyEVMTransaction:
    w3 = Web3(Web3.HTTPProvider(nets.hmy_web3))

    def __init__(self, account: str, tx_hash: hex):
        # identifiers
        self.txHash = tx_hash
        self.account = HarmonyAddress(account)

        # get transaction data
        self.result = HarmonyEVMTransaction.w3.eth.get_transaction(tx_hash)
        self.to_addr = HarmonyAddress(self.result['to'])
        self.from_addr = HarmonyAddress(self.result['from'])

        # temporal data
        self.block = self.result['blockNumber']
        self.timestamp = HarmonyEVMTransaction.get_timestamp(self.block)
        self.block_date = datetime.date.fromtimestamp(self.timestamp)

        # event data
        self.action = HarmonyEVMTransaction.lookup_event(self.result['from'], self.result['to'], account)

        # function argument data
        self.contract_pointer = HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(self.result['to'])
        self.tx_payload = self.contract_pointer.decode_input(self.result['input'])

        # currency data
        self.value = Web3.fromWei(self.result['value'], 'ether')
        self.coinAmount = self.value
        self.receipt = HarmonyEVMTransaction.get_tx_receipt(tx_hash)
        self.tx_fee_in_native_token = Web3.fromWei(self.result['gasPrice'], 'ether') * self.receipt['gasUsed']

        # TODO: fix
        self.fiatValue = 0
        self.fiatFeeValue = 0
        self.fiatType = 'usd'

    @staticmethod
    def lookup_event(fm, to, account) -> str:
        fmStr = contracts.address_map.get(fm, fm) or ""
        toStr = contracts.address_map.get(to, to) or ""
        if '0x' in fmStr and toStr == account:
            fmStr = 'Deposit from {0}'.format(fmStr)
        if '0x' in toStr and fmStr == account:
            toStr = 'Withdrawal to {0}'.format(toStr)

        return "{0} -> {1}".format(fmStr, toStr)

    @classmethod
    def get_timestamp(cls, block):
        try:
            return cls.w3.eth.get_block(block)['timestamp']
        except Exception as err:
            print('Got invalid block {0} {1}'.format(block, str(err)))
            raise err

    @classmethod
    def get_tx_receipt(cls, tx_hash: hex):
        try:
            return cls.w3.eth.get_transaction_receipt(tx_hash)
        except Exception as err:
            print('Got invalid transaction {0} {1}'.format(tx_hash, str(err)))
            raise err

    def tx_payload_to_string(self) -> str:
        decode_successful, function_info = self.tx_payload
        if decode_successful:
            f, _ = function_info

            # escape and strip class name in python to string
            return "\"{0}\"".format(str(f)[1:-1].split(" ")[1])
        else:
            return ""


class walletActivity(HarmonyEVMTransaction):

    @classmethod
    def extract_all_wallet_activity_from_transaction(cls, wallet_address: str, tx_hash: hex) -> List[walletActivity]:
        base_tx_obj = walletActivity(wallet_address, tx_hash)
        token_tx_objs = walletActivity.get_token_activity_from_wallet_activity(base_tx_obj)
        return [base_tx_obj, *token_tx_objs]

    def __init__(self, wallet_address: str, tx_hash: hex, coin_type: str = ""):
        # get information about this tx
        super().__init__(wallet_address, tx_hash)

        self.depositEvent = 'payment' if self.is_payment() else 'deposit'
        self.withdrawalEvent = 'donation' if self.is_donation() else 'withdraw'

        # assume it is ONE unless otherwise specified
        self.coinType = coin_type or contracts.getNativeToken("")

        if self.result['to'] == self.account.get_eth_address() and self.value > 0:
            self.action = self.depositEvent
            self.address = HarmonyAddress(self.result['from'])

        if self.result['from'] == self.account.get_eth_address() and self.value > 0:
            self.action = self.withdrawalEvent
            self.address = HarmonyAddress(self.result['to'])

    def is_payment(self) -> bool:
        return self.result['from'] in contracts.payment_wallets

    def is_donation(self) -> bool:
        return (
                self.result['to'] is not None and
                'Donation' in contracts.getAddressName(self.result['to'])
        )

    def to_csv_row(self, use_one_address: bool) -> str:
        if self.action == 'deposit':
            sentAmount = ''
            sentType = ''
            rcvdAmount = self.coinAmount
            rcvdType = contracts.getAddressName(self.coinType)
        else:
            sentAmount = self.coinAmount
            sentType = contracts.getAddressName(self.coinType)
            rcvdAmount = ''
            rcvdType = ''

        address_format = use_one_address and HarmonyAddress.FORMAT_ONE or HarmonyAddress.FORMAT_ETH
        return ','.join(
            (
                # time of transaction
                KoinlyInterpreter.parse_utc_ts(self.timestamp),

                # token sent in this tx (outgoing)
                str(sentAmount),
                sentType,

                # token received in this tx (incoming)
                str(rcvdAmount),
                rcvdType,

                # gas
                str(self.tx_fee_in_native_token),
                "ONE",

                # fiat conversion
                str(self.fiatValue),
                self.fiatType,
                '',

                # description
                'wallet transfer',

                # transaction hash
                self.txHash,
                self.tx_payload_to_string(),

                # transfer information
                self.to_addr.get_address_str(address_format),
                self.from_addr.get_address_str(address_format),

                '\n'
            )
        )

    @staticmethod
    def get_token_activity_from_wallet_activity(wallet_activity_instance: walletActivity) -> List[walletActivity]:
        return walletActivity._extractTokenResults(
            walletActivity.w3,
            wallet_activity_instance.txHash,
            wallet_activity_instance.account.get_eth_address(),
            wallet_activity_instance.receipt,
            wallet_activity_instance.depositEvent,
            wallet_activity_instance.withdrawalEvent
        )

    @staticmethod
    def _extractTokenResults(w3, txn, account, receipt, depositEvent, withdrawalEvent):
        contract = w3.eth.contract(
            address='0x72Cb10C6bfA5624dD07Ef608027E366bd690048F',
            abi=contracts.getABI('JewelToken')
        )

        decoded_logs = contract.events.Transfer().processReceipt(receipt, errors=DISCARD)

        transfers = []
        for log in decoded_logs:
            if log['args']['from'] == account:
                event = withdrawalEvent
                otherAddress = log['args']['to']
            elif log['args']['to'] == account:
                event = depositEvent
                otherAddress = log['args']['from']
            else:
                continue

            non_native_token_address = log['address']
            non_native_token_amount = log['args']['value']
            tokenValue = contracts.valueFromWei(non_native_token_amount, non_native_token_address)

            r = walletActivity(account, txn, non_native_token_address)
            r.action = event
            r.address = otherAddress
            r.value = tokenValue
            r.coinAmount = tokenValue

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
