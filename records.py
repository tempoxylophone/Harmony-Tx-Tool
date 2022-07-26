from __future__ import annotations
import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Union
from web3 import Web3
from web3.logs import DISCARD
from pyharmony import pyharmony

import nets
from prices import priceLookup
import contracts
from contracts import HarmonyEVMSmartContract
from koinly_interpreter import KoinlyInterpreter
from utils import convert_hex_to_one, convert_one_to_hex


class HarmonyAddress:
    w3 = Web3(Web3.HTTPProvider(nets.hmy_web3))
    FORMAT_ETH = "eth"
    FORMAT_ONE = "one"
    _ADDRESS_DIRECTORY: Dict[str, HarmonyAddress] = {}

    def __init__(self, address: str):
        self.addresses = {
            self.FORMAT_ETH: "",
            self.FORMAT_ONE: "",
        }

        if pyharmony.account.is_valid_address(address):
            # given a one address
            self.address_format = self.FORMAT_ONE
            self.addresses[self.FORMAT_ONE] = address
            self.addresses[self.FORMAT_ETH] = convert_one_to_hex(address)
        elif HarmonyAddress.w3.isAddress(address):
            # given an ethereum address
            self.address_format = self.FORMAT_ETH
            self.addresses[self.FORMAT_ETH] = address
            self.addresses[self.FORMAT_ONE] = convert_hex_to_one(address)
        else:
            raise ValueError("Bad address! Got: {0}".format(address))

        # add to directory
        self._ADDRESS_DIRECTORY[self.get_eth_address()] = self

    def get_address_str(self, address_format: str) -> str:
        return self.addresses[address_format]

    def get_eth_address(self) -> str:
        return self.get_address_str(self.FORMAT_ETH)

    def get_one_address(self) -> str:
        return self.get_address_str(self.FORMAT_ONE)

    @classmethod
    def get_address_string_format(cls, address_string: str) -> str:
        if pyharmony.account.is_valid_address(address_string):
            return cls.FORMAT_ONE
        elif HarmonyAddress.w3.isAddress(address_string):
            return cls.FORMAT_ETH
        else:
            raise ValueError("Bad address, neither eth or one! Got: {0}".format(address_string))

    @property
    def eth(self) -> str:
        return self.get_eth_address()

    @property
    def one(self) -> str:
        return self.get_one_address()

    @classmethod
    def address_str_is_eth(cls, address_str: str) -> bool:
        # also checks if address is neither one or eth, throws ValueError in that case
        return cls.get_address_string_format(address_str) != cls.FORMAT_ETH

    @classmethod
    def get_harmony_address_by_string(cls, address_str: str) -> HarmonyAddress:
        eth_address = cls.address_str_is_eth(address_str) and address_str or convert_one_to_hex(address_str)

        # eth address is always the key
        return cls._ADDRESS_DIRECTORY.get(eth_address, HarmonyAddress(eth_address))

    @classmethod
    def get_harmony_address(cls, address_object: Union[str, HarmonyAddress]) -> HarmonyAddress:
        return address_object if isinstance(address_object, HarmonyAddress) else (
            cls.get_harmony_address_by_string(address_object)
        )

    def __str__(self) -> str:
        # default to eth address format
        return self.get_eth_address()

    def __eq__(self, other):
        return isinstance(other, HarmonyAddress) and self.get_eth_address() and (
                self.get_eth_address() == other.get_eth_address() or
                self.get_one_address() == other.get_one_address()
        )

    def __hash__(self):
        return hash(self.eth)


class HarmonyToken:
    _TOKEN_DIRECTORY: Dict[HarmonyAddress, HarmonyToken] = {}
    _CONV_BTC_ADDRS = {
        '0x3095c7557bCb296ccc6e363DE01b760bA031F2d9',
        '0xdc54046c0451f9269FEe1840aeC808D36015697d'
    }
    _CONV_DFK_GOLD_ADDRS = {
        '0x3a4EDcf3312f44EF027acfd8c21382a5259936e7',
        '0x576C260513204392F0eC0bc865450872025CB1cA'
    }
    _CONV_STABLE_COIN_ADDRS = {
        '0x985458E523dB3d53125813eD68c274899e9DfAb4',
        '0x3C2B8Be99c50593081EAA2A724F0B8285F5aba8f',
        '0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664'
    }

    def __init__(self, address: Union[str, HarmonyAddress], name: Optional[str] = None):
        self.address = HarmonyAddress.get_harmony_address(address)

        self.name = name or contracts.getAddressName(self.address.eth)
        self.ticker = "?"
        self._conversion_unit = self._get_conversion_unit()

        # add self to directory for later
        self._TOKEN_DIRECTORY[self.address] = self

    def __eq__(self, other) -> bool:
        return isinstance(other, HarmonyToken) and self.address == other.address

    def _get_conversion_unit(self) -> str:
        if self.address.eth in self._CONV_BTC_ADDRS:
            return "btc"
        elif self.address.eth in self._CONV_DFK_GOLD_ADDRS:
            return 'kwei'
        elif self.address.eth in self._CONV_STABLE_COIN_ADDRS:
            return 'mwei'
        else:
            return 'ether'

    def get_value_from_wei(self, amount: int) -> Decimal:
        # Simple way to determine conversion, maybe change to lookup on chain later
        # w3.fromWei doesn't seem to have an 8 decimal option for BTC
        return (
                self._conversion_unit == "btc" and amount / Decimal(100000000) or
                Web3.fromWei(amount, self._conversion_unit)
        )

    @classmethod
    def get_harmony_token_by_address(cls, address: Union[HarmonyAddress, str]) -> HarmonyToken:
        return cls._TOKEN_DIRECTORY.get(
            address,
            # use the eth address as default ticker as placeholder
            HarmonyToken(address)
        )


class HarmonyEVMTransaction:
    w3 = Web3(Web3.HTTPProvider(nets.hmy_web3))

    def __init__(self, account: Union[HarmonyAddress, str], tx_hash: hex):
        # identifiers
        self.txHash = tx_hash
        self.account = HarmonyAddress.get_harmony_address(account)

        # get transaction data
        self.result = HarmonyEVMTransaction.w3.eth.get_transaction(tx_hash)
        self.to_addr = HarmonyAddress.get_harmony_address(self.result['to'])
        self.from_addr = HarmonyAddress.get_harmony_address(self.result['from'])

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

    def __init__(
            self,
            wallet_address: Union[HarmonyAddress, str],
            tx_hash: hex,
            harmony_token: Optional[HarmonyToken] = None
    ):
        # get information about this tx
        super().__init__(wallet_address, tx_hash)

        self.depositEvent = 'payment' if self.is_payment() else 'deposit'
        self.withdrawalEvent = 'donation' if self.is_donation() else 'withdraw'

        # assume it is ONE unless otherwise specified
        self.coinType = harmony_token or HarmonyToken.get_harmony_token_by_address(contracts.getNativeToken(""))

        if self.to_addr == self.account and self.value > 0:
            self.action = self.depositEvent
            self.address = HarmonyAddress.get_harmony_address(self.result['from'])

        if self.from_addr == self.account and self.value > 0:
            self.action = self.withdrawalEvent
            self.address = HarmonyAddress.get_harmony_address(self.result['to'])

    def is_payment(self) -> bool:
        return self.result['from'] in contracts.payment_wallets

    def is_donation(self) -> bool:
        return (
                self.result['to'] is not None and
                'Donation' in contracts.getAddressName(self.result['to'])
        )

    def get_fiat_value(self) -> Decimal:
        # TODO: fix
        return priceLookup(self.timestamp, self.coinType.address.eth, self.fiatType)

    def to_csv_row(self, use_one_address: bool) -> str:
        if self.action == 'deposit':
            sentAmount = ''
            sentType = ''
            rcvdAmount = self.coinAmount
            rcvdType = self.coinType.name
        else:
            sentAmount = self.coinAmount
            sentType = self.coinType.name
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
                str(self.get_fiat_value()),
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
            wallet_activity_instance.account,
            wallet_activity_instance.receipt,
            wallet_activity_instance.depositEvent,
            wallet_activity_instance.withdrawalEvent
        )

    @staticmethod
    def _extractTokenResults(w3, txn, account_address: HarmonyAddress, receipt, depositEvent, withdrawalEvent):
        contract = w3.eth.contract(
            address='0x72Cb10C6bfA5624dD07Ef608027E366bd690048F',
            abi=contracts.getABI('JewelToken')
        )

        decoded_logs = contract.events.Transfer().processReceipt(receipt, errors=DISCARD)

        transfers = []
        for log in decoded_logs:
            if log['args']['from'] == account_address.eth:
                event = withdrawalEvent
                otherAddress = HarmonyAddress(log['args']['to'])
            elif log['args']['to'] == account_address.eth:
                event = depositEvent
                otherAddress = HarmonyAddress(log['args']['from'])
            else:
                continue

            non_native_token = HarmonyToken.get_harmony_token_by_address(log['address'])
            tokenValue = non_native_token.get_value_from_wei(log['args']['value'])

            r = walletActivity(account_address, txn, non_native_token)
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
