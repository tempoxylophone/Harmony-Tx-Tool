from __future__ import annotations
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional, Union, Tuple, Iterable, Any
from collections import defaultdict
from functools import lru_cache

import requests
from web3 import Web3
from web3.contract import ContractFunction
from web3.logs import DISCARD
from web3.types import TxReceipt, EventData, HexStr
from pyharmony import pyharmony

import contracts
from utils import api_retry, get_local_abi
from dex import UniswapForkGraph


class HarmonyAPI:
    HARMONY_LAUNCH_DATE: date = datetime.strptime("2019-05-01", '%Y-%m-%d').date()
    _NET_HMY_MAIN = 'https://api.harmony.one'
    _NET_HMY_WEB3 = 'https://api.harmony.one'

    _w3 = Web3(Web3.HTTPProvider(_NET_HMY_WEB3))
    _ERC20_ABI = get_local_abi('ERC20')

    _JEWEL_CONTRACT = _w3.eth.contract(  # noqa
        address='0x72Cb10C6bfA5624dD07Ef608027E366bd690048F',
        abi=get_local_abi('JewelToken')
    )

    @classmethod
    @api_retry()
    def get_transaction(cls, tx_hash: Union[HexStr, str]):
        return cls._w3.eth.get_transaction(tx_hash)

    @classmethod
    @api_retry()
    def get_timestamp(cls, block: int):
        try:
            return cls._w3.eth.get_block(block)['timestamp']
        except Exception as err:
            print('Got invalid block {0} {1}'.format(block, str(err)))
            raise err

    @classmethod
    @api_retry()
    def get_tx_receipt(cls, tx_hash: Union[HexStr, str]) -> TxReceipt:
        try:
            return cls._w3.eth.get_transaction_receipt(tx_hash)
        except Exception as err:
            print('Got invalid transaction {0} {1}'.format(tx_hash, str(err)))
            raise err

    @classmethod
    @api_retry()
    def get_tx_transfer_logs(cls, tx_receipt: TxReceipt) -> Iterable[EventData]:
        return cls._JEWEL_CONTRACT.events.Transfer().processReceipt(
            tx_receipt,
            errors=DISCARD
        )

    @classmethod
    @api_retry()
    def get_token_info(cls, token_eth_address: str) -> Tuple[str, int, str]:
        contract = cls._w3.eth.contract(  # noqa
            address=Web3.toChecksumAddress(token_eth_address),
            abi=cls._ERC20_ABI
        )
        try:
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            name = contract.functions.name().call()
            return symbol, decimals, name
        except Exception as err:
            print('Failed to get token info for {0} - ERROR: {1}'.format(token_eth_address, err))
            return '?', 18, '?'

    @staticmethod
    def get_harmony_tx_list(eth_address: str, page_size: int = 1_000) -> List[str]:
        offset = 0
        txs = []
        has_more = True
        while has_more:
            results = pyharmony.account.get_transaction_history(
                eth_address,
                page=offset,
                page_size=page_size,
                include_full_tx=False,
                endpoint=HarmonyAPI._NET_HMY_MAIN
            ) or []
            has_more = bool(results)
            offset += 1
            txs += results

        # de-dupe tx hashes in order
        return list(dict.fromkeys(txs))

    @staticmethod
    def get_num_tx_for_wallet(eth_address: str) -> int:
        return pyharmony.account.get_transaction_count(
            eth_address,
            'latest',
            endpoint=HarmonyAPI._NET_HMY_MAIN
        )


class HarmonyAddress:
    FORMAT_ETH = "eth"
    FORMAT_ONE = "one"
    _HARMONY_BECH32_HRP = "one"
    _ADDRESS_DIRECTORY: Dict[str, HarmonyAddress] = {}

    def __init__(self, address: str):
        self.addresses = {
            self.FORMAT_ETH: "",
            self.FORMAT_ONE: "",
        }

        if self.is_valid_one_address(address):
            # given a one address
            self.address_format = self.FORMAT_ONE
            self.addresses[self.FORMAT_ONE] = address
            self.addresses[self.FORMAT_ETH] = self.convert_one_to_hex(address)
        elif self.is_valid_eth_address(address):
            # given an ethereum address
            self.address_format = self.FORMAT_ETH
            self.addresses[self.FORMAT_ETH] = address
            self.addresses[self.FORMAT_ONE] = self.convert_hex_to_one(address)
        else:
            raise ValueError("Bad address! Got: {0}".format(address))

        # add to directory
        HarmonyAddress._ADDRESS_DIRECTORY[self.eth] = self

    def get_address_str(self, address_format: str) -> str:
        return self.addresses[address_format]

    def get_eth_address(self) -> str:
        return self.get_address_str(self.FORMAT_ETH)

    def get_one_address(self) -> str:
        return self.get_address_str(self.FORMAT_ONE)

    @property
    def eth(self) -> str:
        return self.get_eth_address()

    @property
    def one(self) -> str:
        return self.get_one_address()

    @classmethod
    def get_address_string_format(cls, address_string: str) -> str:
        if cls.is_valid_one_address(address_string):
            return cls.FORMAT_ONE
        elif cls.is_valid_eth_address(address_string):
            return cls.FORMAT_ETH
        else:
            raise ValueError("Bad address, neither eth or one! Got: {0}".format(address_string))

    @classmethod
    def address_str_is_eth(cls, address_str: str) -> bool:
        # also checks if address is neither one or eth, throws ValueError in that case
        return cls.get_address_string_format(address_str) != cls.FORMAT_ETH

    @classmethod
    def get_harmony_address_by_string(cls, address_str: str) -> HarmonyAddress:
        eth_address = (cls.address_str_is_eth(address_str) and address_str or cls.convert_one_to_hex(address_str))

        # if given a lowercase address, clean it
        eth_address = Web3.toChecksumAddress(eth_address)

        # eth address is always the key
        return HarmonyAddress._ADDRESS_DIRECTORY.get(eth_address) or HarmonyAddress(eth_address)

    @classmethod
    def get_harmony_address(cls, address_object: Union[str, HarmonyAddress]) -> HarmonyAddress:
        return address_object if isinstance(address_object, HarmonyAddress) else (
            cls.get_harmony_address_by_string(address_object)
        )

    @classmethod
    def convert_one_to_hex(cls, one_string_hash: str) -> str:
        return pyharmony.util.convert_one_to_hex(one_string_hash)

    @classmethod
    def convert_hex_to_one(cls, eth_string_hash: str) -> str:
        p = bytearray.fromhex(
            # remove 0x prefix from ethereum hash if necessary
            eth_string_hash[2:] if eth_string_hash.startswith("0x") else eth_string_hash
        )

        # encode to bech32 style hash "one" hash
        return pyharmony.bech32.bech32_encode(
            cls._HARMONY_BECH32_HRP,
            pyharmony.bech32.convertbits(p, 8, 5)
        )

    @classmethod
    def is_valid_one_address(cls, address: str) -> bool:
        return pyharmony.account.is_valid_address(address)

    @classmethod
    def is_valid_eth_address(cls, address: str) -> bool:
        # doesn't make any calls to the internet so I am fine leaving it on this class
        return HarmonyAPI._w3.isAddress(address)  # noqa

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


class DexPriceManager:
    _TX_LOOKUP: Dict[HarmonyToken, Union[List, float, Dict]] = defaultdict(lambda: {
        'blocks': [],
        'timestamps': [],
        'max_timestamp': float("-inf"),
        'min_timestamp': float("+inf"),
        'fiat_prices_by_block': {},
    })
    _DEX_GRAPH_URLS = [
        # order matters, attempts for lookups made first at the front
        'https://graph.viper.exchange/subgraphs/name/venomprotocol/venomswap-v2',  # VIPERSWAP
        'https://defi-kingdoms-community-api-gateway-co06z8vi.uc.gateway.dev/graphql',  # DEFIKINGDOMS
    ]
    _DEX_GRAPHS = [UniswapForkGraph(x) for x in _DEX_GRAPH_URLS]

    @classmethod
    def get_price_of_token_at_block(cls, token: HarmonyToken, block: int) -> Decimal:
        return cls._TX_LOOKUP[token]['fiat_prices_by_block'][block]

    @staticmethod
    def initialize_static_price_manager(transactions: Iterable[HarmonyEVMTransaction]) -> None:
        DexPriceManager._build_transactions_directory(transactions)
        DexPriceManager._build_transactions_fiat_price_lookup()

    @staticmethod
    def _build_transactions_directory(transactions: Iterable[HarmonyEVMTransaction]) -> None:
        for t in transactions:
            if not isinstance(t, HarmonyEVMTransaction):
                continue

            p = DexPriceManager._TX_LOOKUP[t.coinType]

            timestamp = t.timestamp
            p['blocks'].append(t.block)
            p['timestamps'].append(timestamp)
            p['max_timestamp'] = max(p['max_timestamp'], timestamp)
            p['min_timestamp'] = min(p['min_timestamp'], timestamp)

    @classmethod
    def get_token_or_pair_info(cls, token_or_pair_address: str) -> Dict:
        for dex in DexPriceManager._DEX_GRAPHS:
            # try to get token information from any dex we can until we get useful
            # data back
            info = cls._try_to_get_token_or_pair_info_from_dexes(dex, token_or_pair_address)

            if DexPriceManager._is_valid_token_or_pair_info(info):
                return info

        return {}

    @classmethod
    def _try_to_get_token_or_pair_info_from_dexes(cls, dex_graph: UniswapForkGraph, token_address: str) -> Dict:
        return dex_graph.get_token_or_pair_info(
            token_address,
        )

    @staticmethod
    def _is_valid_token_or_pair_info(token_or_pair_info: Dict) -> bool:
        pair_info = token_or_pair_info['pair']
        token_info = token_or_pair_info['token']

        if not bool(pair_info) and not bool(token_info):
            # at least one must be non-null for this to be considered a reasonable response
            return False

        return True

    @staticmethod
    def _build_transactions_fiat_price_lookup() -> None:
        if len(DexPriceManager._TX_LOOKUP) == 0:
            raise ValueError(
                "Transactions lookup has not been built. Call build_transactions_directory() first"
            )

        for harmony_token, token_properties in DexPriceManager._TX_LOOKUP.items():
            for dex in DexPriceManager._DEX_GRAPHS:
                # try to get token information from any dex we can until we get useful
                # data back
                if harmony_token.is_lp_token:
                    ts = DexPriceManager._try_to_get_lp_prices_from_dexes(
                        dex,
                        harmony_token.address.eth,
                        token_properties['min_timestamp'],
                        token_properties['max_timestamp'],
                        token_properties['blocks'],
                    )
                else:
                    ts = DexPriceManager._try_to_get_token_prices_from_dexes(
                        dex,
                        harmony_token.address.eth,
                        token_properties['blocks'],
                    )

                if DexPriceManager._is_valid_price_timeseries(ts):
                    token_properties['fiat_prices_by_block'] = ts
                    break

    @staticmethod
    def _try_to_get_token_prices_from_dexes(
            dex_graph: UniswapForkGraph,
            token_address: str,
            blocks: Iterable[int]) -> Dict:
        return dex_graph.get_token_price_by_block_timeseries(
            token_address,
            blocks,
        )

    @staticmethod
    def _try_to_get_lp_prices_from_dexes(
            dex_graph: UniswapForkGraph,
            token_address: str,
            min_ts: int,
            max_ts: int,
            blocks: Iterable[int]
    ) -> Dict:
        return dex_graph.get_lp_token_price_by_block_timeseries(
            token_address,
            min_ts,
            max_ts,
            blocks,
        )

    @staticmethod
    def _is_valid_price_timeseries(price_timeseries: Dict) -> bool:
        # TODO: add failure criteria
        return True


class HarmonyToken:
    NATIVE_TOKEN_SYMBOL = "ONE"
    NATIVE_TOKEN_ETH_ADDRESS_STR = "0xcF664087a5bB0237a0BAd6742852ec6c8d69A27a"
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

    @classmethod
    def native_token(cls):
        return cls.get_harmony_token_by_address(cls.NATIVE_TOKEN_ETH_ADDRESS_STR)

    def __init__(
            self,
            address: Union[str, HarmonyAddress],
            merge_one_wone_names: Optional[bool] = True
    ):
        self.address = HarmonyAddress.get_harmony_address(address)

        symbol, decimals, name = HarmonyAPI.get_token_info(self.address.eth)
        self.name = name or contracts.getAddressName(self.address.eth)
        self.symbol = symbol
        self.decimals = decimals

        self._conversion_unit = self._get_conversion_unit()

        # DEX stuff
        self.is_lp_token = False
        self.lp_token_0 = None
        self.lp_token_1 = None

        if self.symbol == "WONE":
            # consider WONE and ONE equivalent by symbol
            if merge_one_wone_names:
                self.symbol = self.NATIVE_TOKEN_SYMBOL
        else:
            # if not a native currency, try to see if it an LP position
            self._set_is_lp_token_guess()

        # add self to directory for later
        HarmonyToken._TOKEN_DIRECTORY[self.address] = self

    def _set_is_lp_token_guess(self):
        dex_info = DexPriceManager.get_token_or_pair_info(self.address.eth)
        pair_info = dex_info['pair']
        token_info = dex_info['token']

        self.is_lp_token = self._is_pair(pair_info, token_info)

        if self.is_lp_token:
            token_0_eth_address = pair_info['token0']['id']
            token_1_eth_address = pair_info['token1']['id']
            self.lp_token_0 = HarmonyToken.get_harmony_token_by_address(token_0_eth_address)
            self.lp_token_0 = HarmonyToken.get_harmony_token_by_address(token_1_eth_address)

    @staticmethod
    def _is_pair(pair_info, token_info) -> bool:
        if bool(pair_info) ^ bool(token_info):
            # if there is only 1 result given the address
            return bool(pair_info)

        # we got an answer back for both a token and an LP pair at the same address
        # this is rare but can happen
        token_trade_vol_usd = token_info['tradeVolumeUSD']
        token_tx_count = token_info['txCount']
        token_total_liquidity = token_info['totalLiquidity']
        if token_trade_vol_usd < 1 and token_total_liquidity < 10 and token_tx_count < 100:
            # somewhat hacky solution but check if the single token has unusually
            # low activity. Someone may have created this by mistake, in which
            # case we should prefer the pair's info
            return True

        # this looks more like a token than an LP position
        return False

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
        addr_obj = HarmonyAddress.get_harmony_address(address)
        return HarmonyToken._TOKEN_DIRECTORY.get(
            addr_obj
        ) or HarmonyToken(addr_obj)

    def __str__(self) -> str:
        return "HarmonyToken: {0} ({1}) [{2}]".format(self.symbol, self.name, self.address.eth)

    def __eq__(self, other) -> bool:
        return isinstance(other, HarmonyToken) and self.address == other.address

    def __hash__(self):
        return hash("harmony_token" + str(self.address.__hash__()))


class HarmonyEVMTransaction:

    def __init__(self, account: Union[HarmonyAddress, str], tx_hash: hex):
        # identifiers
        self.txHash = tx_hash
        self.account = HarmonyAddress.get_harmony_address(account)

        # get transaction data
        self.result = HarmonyAPI.get_transaction(tx_hash)
        self.to_addr = HarmonyAddress.get_harmony_address(self.result['to'])
        self.from_addr = HarmonyAddress.get_harmony_address(self.result['from'])

        # temporal data
        self.block = self.result['blockNumber']
        self.timestamp = HarmonyEVMTransaction.get_timestamp(self.block)
        self.block_date = date.fromtimestamp(self.timestamp)

        # event data
        self.action = HarmonyEVMTransaction.lookup_event(self.result['from'], self.result['to'], str(account))

        # function argument data
        self.contract_pointer = HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(self.result['to'])
        self.tx_payload = self.contract_pointer.decode_input(self.result['input'])

        # currency data
        self.value = Web3.fromWei(self.result['value'], 'ether')
        self.coinAmount = self.value

        # assume it is ONE unless otherwise specified, inheritors of this class can change
        # this based data relevant to what they do
        self.coinType = HarmonyToken.native_token()

        self.receipt = HarmonyEVMTransaction.get_tx_receipt(tx_hash)
        self.tx_fee_in_native_token = Web3.fromWei(self.result['gasPrice'], 'ether') * self.receipt['gasUsed']

        # TODO: fix
        self.fiatValue = 0
        self.fiatFeeValue = 0
        self.fiatType = 'usd'

    def get_fiat_value(self) -> Decimal:
        token_price = DexPriceManager.get_price_of_token_at_block(self.coinType, self.block)
        token_qty = self.value * token_price

        fee_price = DexPriceManager.get_price_of_token_at_block(HarmonyToken.native_token(), self.block)
        fee_qty = self.tx_fee_in_native_token

        return token_qty * token_price + fee_price * fee_qty

    @staticmethod
    def lookup_event(fm_addr: str, to_addr: str, account) -> str:
        fmStr = contracts.address_map.get(fm_addr, fm_addr) or ""
        toStr = contracts.address_map.get(to_addr, to_addr) or ""
        if '0x' in fmStr and toStr == account:
            fmStr = 'Deposit from {0}'.format(fmStr)
        if '0x' in toStr and fmStr == account:
            toStr = 'Withdrawal to {0}'.format(toStr)

        return "{0} -> {1}".format(fmStr, toStr)

    @classmethod
    def get_timestamp(cls, block) -> int:
        return HarmonyAPI.get_timestamp(block)

    @classmethod
    def get_tx_receipt(cls, tx_hash: hex) -> Dict:
        return HarmonyAPI.get_tx_receipt(tx_hash)

    def get_tx_function_signature(self) -> str:
        decode_successful, function_info = self.tx_payload
        if decode_successful:
            f, _ = function_info

            # escape and strip class name in python to string
            return "\"{0}\"".format(str(f)[1:-1].split(" ")[1])
        else:
            return ""


T_DECODED_ETH_SIG = Tuple[ContractFunction, Dict[str, Any]]


class HarmonyEVMSmartContract:
    w3 = HarmonyAPI._w3  # noqa
    API_NOT_FOUND_MESSAGES = {"Not found", "contract not found"}
    ABI_API_ENDPOINT = "https://ctrver.t.hmny.io/fetchContractCode?contractAddress={0}&shard=0"
    POSSIBLE_ABIS = [
        "ERC20",
        "ERC721",
        "UniswapV2Router02",
        "USD Coin",
        "Wrapped ONE"
    ]

    @classmethod
    @lru_cache(maxsize=256)
    def lookup_harmony_smart_contract_by_address(cls, address: str, name: str = "") -> HarmonyEVMSmartContract:
        return HarmonyEVMSmartContract(address, name)

    def __init__(self, address: str, assigned_name: str):
        self.address = address
        self.name = assigned_name

        # contract function requires us to know interface of source
        self.code = HarmonyEVMSmartContract.get_code(address)
        self.has_code = not self._is_missing(self.code)
        self.abi = self.has_code and self.code['abi'] or get_local_abi(self.POSSIBLE_ABIS[0])
        self.abi_attempt_idx = 1
        self.contract = HarmonyEVMSmartContract.w3.eth.contract(  # noqa
            Web3.toChecksumAddress(self.address),
            abi=self.abi
        )

    def decode_input(self, tx_input: hex) -> Tuple[bool, Union[T_DECODED_ETH_SIG, None]]:
        if self.abi_attempt_idx > len(self.POSSIBLE_ABIS) - 1:
            # can't decode this, even after trying a few generic ABIs
            return False, None

        try:
            f = self.contract.decode_function_input(tx_input)
            return True, f
        except ValueError:
            # can't decode this input, keep shuffling different ABIs until get match, then stop
            self.abi = get_local_abi(self.POSSIBLE_ABIS[self.abi_attempt_idx])
            self.abi_attempt_idx += 1
            return self.decode_input(tx_input)

    @staticmethod
    @lru_cache(maxsize=256)
    def get_code(address: str) -> Dict:
        url = HarmonyEVMSmartContract.get_code_request_url(address)
        return requests.get(url).json()

    @staticmethod
    def get_code_request_url(address: str) -> str:
        return HarmonyEVMSmartContract.ABI_API_ENDPOINT.format(address)

    @staticmethod
    def _is_missing(code) -> bool:
        return code.get("message") in HarmonyEVMSmartContract.API_NOT_FOUND_MESSAGES
