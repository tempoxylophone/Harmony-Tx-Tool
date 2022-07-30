from __future__ import annotations
from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional, Union, Tuple, Iterable, Any, TypedDict
from functools import lru_cache
from collections import defaultdict

import requests

from hexbytes import HexBytes
from web3 import Web3
from web3.contract import ContractFunction, Contract
from web3.logs import DISCARD
from web3.types import TxReceipt, EventData, HexStr
from web3.exceptions import BadFunctionCallOutput, TransactionNotFound, BlockNotFound

from txtool import pyhmy
from txtool.utils import api_retry, get_local_abi, MAIN_LOGGER, make_yellow
from txtool.dex import UniswapV2ForkGraph


class HarmonyAPI:
    _CUSTOM_EXCEPTIONS: List = [
        pyhmy.rpc.exceptions.RPCError,
        pyhmy.rpc.exceptions.RequestsError,
    ]
    _NET_HMY_MAIN = "https://api.harmony.one"
    _NET_HMY_WEB3 = "https://api.harmony.one"

    _w3 = Web3(Web3.HTTPProvider(_NET_HMY_WEB3))
    _ERC20_ABI = get_local_abi("ERC20")

    _JEWEL_CONTRACT = _w3.eth.contract(  # noqa
        address="0x72Cb10C6bfA5624dD07Ef608027E366bd690048F",  # type: ignore
        abi=get_local_abi("JewelToken"),
    )

    API_NOT_FOUND_MESSAGES = {"Not found", "contract not found"}
    ABI_API_ENDPOINT = (
        "https://ctrver.t.hmny.io/fetchContractCode?contractAddress={0}&shard=0"
    )

    @classmethod
    @lru_cache(maxsize=128)
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_transaction(cls, tx_hash: HexStr):
        return cls._w3.eth.get_transaction(tx_hash)

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_timestamp(cls, block: int):
        if block < 1:
            raise ValueError("Invalid block... must be at least 1")

        try:
            return cls._w3.eth.get_block(block)["timestamp"]
        except BlockNotFound as err:
            raise ValueError(
                "Got invalid block {0} {1} - this block may not exist yet.".format(
                    block, str(err)
                )
            ) from err

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_tx_receipt(cls, tx_hash: HexStr) -> TxReceipt:
        try:
            return cls._w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound as err:
            raise ValueError(
                "Can't find transaction with hash: {0} ."
                "Invalid transaction {0} {1}".format(tx_hash, str(err))
            ) from err

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_tx_transfer_logs(cls, tx_receipt: TxReceipt) -> Iterable[EventData]:
        return cls._JEWEL_CONTRACT.events.Transfer().processReceipt(
            tx_receipt, errors=DISCARD
        )

    @classmethod
    @lru_cache(maxsize=256)
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_token_info(cls, token_eth_address: str) -> Tuple[str, int, str]:
        contract = cls._w3.eth.contract(  # noqa
            address=Web3.toChecksumAddress(token_eth_address), abi=cls._ERC20_ABI
        )
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        name = contract.functions.name().call()
        return symbol, decimals, name

    @staticmethod
    def has_token_info(eth_address: str) -> bool:
        try:
            symbol, decimals, name = HarmonyAPI.get_token_info(eth_address)
            # items with 0 decimals are 1 of 1
            return bool(symbol and name) and decimals >= 0
        except BadFunctionCallOutput:
            return False

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_smart_contract_byte_code(cls, eth_address: str) -> HexBytes:
        return cls._w3.eth.get_code(eth_address)

    @staticmethod
    def address_belongs_to_smart_contract(eth_address: str) -> bool:
        # null byte if address belongs to a wallet
        # this will return True if this is the address of ERC20 token
        return bool(HarmonyAPI.get_smart_contract_byte_code(eth_address))

    @staticmethod
    def address_belongs_to_erc_20_token(eth_address: str) -> bool:
        return HarmonyAPI.address_belongs_to_smart_contract(
            eth_address
        ) and HarmonyAPI.has_token_info(eth_address)

    @staticmethod
    def get_harmony_tx_list(
        eth_address: str, dt_ts_lb: int, dt_ts_ub: int, page_size: int = 1_000
    ) -> List[HexStr]:
        txs = []
        num_tx = HarmonyAPI.get_num_tx_for_wallet(eth_address)
        num_pages = num_tx // page_size

        for p_idx in range(num_pages):
            results = HarmonyAPI._get_tx_page(eth_address, p_idx, page_size)
            new_txs = [
                x["hash"] for x in results if dt_ts_lb <= x["timestamp"] <= dt_ts_ub
            ]
            txs += new_txs

            MAIN_LOGGER.info(
                "got page %s/%s of all wallet transactions. Total tx = %s...",
                p_idx + 1,
                num_pages,
                len(txs),
            )

            if len(new_txs) < page_size:  # pragma: no cover
                # we reached oob
                break

        # de-dupe tx hashes in order, sometimes API returns duplicates in pagination
        MAIN_LOGGER.info("Done fetching transactions from API.")
        return list(dict.fromkeys(txs))

    @staticmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def _get_tx_page(
        eth_address: str, page_num: int, page_size: int, order: Optional[str] = "DESC"
    ) -> List[Dict]:
        # order can be: "DESC" or "ASC"
        # docs: https://api.hmny.io/#:~:text=POSThmyv2_getTransactionsHistory
        return (
            pyhmy.account.get_transaction_history(
                eth_address,
                page=page_num,
                page_size=page_size,
                include_full_tx=True,
                endpoint=HarmonyAPI._NET_HMY_MAIN,
                order=order,
            )
            or []
        )

    @staticmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_num_tx_for_wallet(eth_address: str) -> int:
        return pyhmy.account.get_transaction_count(
            eth_address, "latest", endpoint=HarmonyAPI._NET_HMY_MAIN
        )

    @classmethod
    @lru_cache(maxsize=256)
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_code(cls, address: str) -> Dict:
        url = cls._get_code_request_url(address)
        return requests.get(url).json()

    @classmethod
    def _get_code_request_url(cls, address: str) -> str:
        return cls.ABI_API_ENDPOINT.format(address)

    @classmethod
    def get_contract(cls, address: str, abi: str) -> Contract:
        return cls._w3.eth.contract(Web3.toChecksumAddress(address), abi=abi)

    @classmethod
    def is_eth_address(cls, address: str) -> bool:
        return cls._w3.isAddress(address)


class HarmonyAddress:
    FORMAT_ETH = "eth"
    FORMAT_ONE = "one"
    _HARMONY_BECH32_HRP = "one"
    _ADDRESS_DIRECTORY: Dict[str, HarmonyAddress] = {}

    def __init__(self, eth_address: str, merge_one_wone_names: Optional[bool] = True):
        self.addresses = {
            self.FORMAT_ETH: "",
            self.FORMAT_ONE: "",
        }

        if self.is_valid_eth_address(eth_address):
            # given an ethereum address
            self.address_format = self.FORMAT_ETH
            self.addresses[self.FORMAT_ETH] = eth_address
            self.addresses[self.FORMAT_ONE] = self.convert_hex_to_one(eth_address)
        elif self.is_valid_one_address(eth_address):
            raise ValueError(
                "Use ETH address, not ONE address! Got: {0}".format(eth_address)
            )
        else:
            raise ValueError("Bad address! Got: {0}".format(eth_address))

        MAIN_LOGGER.info(
            "Encountered new address: %s. Address book now contains: %s addresses",
            eth_address,
            len(HarmonyAddress._ADDRESS_DIRECTORY),
        )

        # add to directory
        HarmonyAddress._ADDRESS_DIRECTORY[self.eth] = self

        self.belongs_to_smart_contract = HarmonyAPI.address_belongs_to_smart_contract(
            self.eth
        )

        # this will be set if the address is called in the constructor of token
        self.belongs_to_token = (
            self.belongs_to_smart_contract
            and HarmonyAPI.address_belongs_to_erc_20_token(self.eth)
        )

        self.token = None
        if self.belongs_to_token:
            self.token = HarmonyToken.get_harmony_token_by_address(
                self.eth, merge_one_wone_names
            )

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

    @property
    def belongs_to_non_token_smart_contract(self) -> bool:
        return self.belongs_to_smart_contract and not self.belongs_to_token

    @classmethod
    def get_address_string_format(cls, address_string: str) -> str:
        if cls.is_valid_one_address(address_string):
            return cls.FORMAT_ONE
        if cls.is_valid_eth_address(address_string):
            return cls.FORMAT_ETH
        raise ValueError(
            "Bad address, neither eth or one! Got: {0}".format(address_string)
        )

    @classmethod
    def address_str_is_eth(cls, address_str: str) -> bool:
        # also checks if address is neither one or eth, throws ValueError in that case
        return cls.get_address_string_format(address_str) == cls.FORMAT_ETH

    @classmethod
    def get_harmony_address_by_string(
        cls, address_str: str, merge_one_wone_names: Optional[bool] = True
    ) -> HarmonyAddress:
        eth_address = (
            address_str
            if cls.address_str_is_eth(address_str)
            else cls.convert_one_to_hex(address_str)
        )

        # if given a lowercase address, clean it
        eth_address = Web3.toChecksumAddress(eth_address)

        # eth address is always the key
        return HarmonyAddress._ADDRESS_DIRECTORY.get(eth_address) or HarmonyAddress(
            eth_address, merge_one_wone_names
        )

    @classmethod
    def get_harmony_address(
        cls,
        address_object: Union[str, HarmonyAddress],
        merge_one_wone_names: Optional[bool] = True,
    ) -> HarmonyAddress:
        return (
            address_object
            if isinstance(address_object, HarmonyAddress)
            else (
                cls.get_harmony_address_by_string(address_object, merge_one_wone_names)
            )
        )

    @classmethod
    def convert_one_to_hex(cls, one_string_hash: str) -> str:
        return pyhmy.util.convert_one_to_hex(one_string_hash)

    @classmethod
    def convert_hex_to_one(cls, eth_string_hash: str) -> str:
        return pyhmy.util.convert_hex_to_one(eth_string_hash)

    @classmethod
    def is_valid_one_address(cls, address: str) -> bool:
        return pyhmy.account.is_valid_address(address)

    @classmethod
    def is_valid_eth_address(cls, address: str) -> bool:
        return HarmonyAPI.is_eth_address(address)

    @staticmethod
    def clean_eth_address_str(eth_address_str: str) -> str:
        return Web3.toChecksumAddress(eth_address_str)

    def __str__(self) -> str:
        # default to eth address format
        return self.get_eth_address()

    def __eq__(self, other):
        return (
            isinstance(other, HarmonyAddress)
            and self.get_eth_address()
            and (
                self.get_eth_address() == other.get_eth_address()
                or self.get_one_address() == other.get_one_address()
            )
        )

    def __hash__(self):
        return hash(self.eth)


class DexPriceManager:
    class DexPriceInfo(TypedDict):
        blocks: List[int]
        timestamps: List[int]
        timestamp_range: Dict[str, Union[float, int]]
        fiat_prices_by_block: Dict[int, Decimal]

    _TX_LOOKUP: Dict[HarmonyToken, DexPriceInfo] = defaultdict(
        lambda: {
            "blocks": [],
            "timestamps": [],
            "timestamp_range": {
                "max": float("-inf"),
                "min": float("+inf"),
            },
            "fiat_prices_by_block": {},
        }
    )
    _DEX_GRAPH_URLS = [
        # order matters, attempts for lookups made first at the front
        # VIPERSWAP
        (
            "https://graph.viper.exchange/subgraphs/name/venomprotocol/venomswap-v2",
            "graph.viper.exchange",
            "https://info.viper.exchange",
        ),
        # # DEFIKINGDOMS
        # UPDATE: not a uniswap graph
        # # see docs: https://devs.defikingdoms.com/api/community-graphql-api/getting-started
        # (
        #     "https://defi-kingdoms-community-api-gateway-co06z8vi.uc.gateway.dev/graphql",
        # ),
    ]
    _DEX_GRAPHS = [UniswapV2ForkGraph(*x) for x in _DEX_GRAPH_URLS]

    @classmethod
    def get_price_of_token_at_block(cls, token: HarmonyToken, block: int) -> Decimal:
        return cls._TX_LOOKUP[token]["fiat_prices_by_block"][block]

    @classmethod
    def initialize_static_price_manager(
        cls,
        transactions: Iterable[HarmonyEVMTransaction],
    ) -> None:
        DexPriceManager._build_transactions_directory(transactions)
        DexPriceManager._build_transactions_fiat_price_lookup()

    @staticmethod
    def _build_transactions_directory(
        transactions: Iterable[HarmonyEVMTransaction],
    ) -> None:
        for t in transactions:
            # ensure ONE is included for this block so we can look up gas
            tokens = [t.coinType] + (
                not t.coinType.is_native_token and [HarmonyToken.native_token()] or []
            )

            for token in tokens:
                timestamp = t.timestamp
                p = DexPriceManager._TX_LOOKUP[token]
                p["blocks"].append(t.block)
                p["timestamps"].append(timestamp)
                p["timestamp_range"]["max"] = max(
                    p["timestamp_range"]["max"], timestamp
                )
                p["timestamp_range"]["min"] = min(
                    p["timestamp_range"]["min"], timestamp
                )

    @classmethod
    def get_token_or_pair_info(cls, token_or_pair_address: str) -> Dict:
        for dex in DexPriceManager._DEX_GRAPHS:
            # try to get token information from any dex we can until we get useful
            # data back
            info = cls._try_to_get_token_or_pair_info_from_dexes(
                dex, token_or_pair_address
            )

            if DexPriceManager._is_valid_token_or_pair_info(info):
                return info

        return {}

    @classmethod
    def _try_to_get_token_or_pair_info_from_dexes(
        cls, dex_graph: UniswapV2ForkGraph, token_address: str
    ) -> Dict:
        return dex_graph.get_token_or_pair_info(
            token_address,
        )

    @staticmethod
    def _is_valid_token_or_pair_info(token_or_pair_info: Dict) -> bool:
        pair_info = token_or_pair_info["pair"]
        token_info = token_or_pair_info["token"]

        if not bool(pair_info) and not bool(token_info):
            # at least one must be non-null for this to be considered a reasonable response
            return False

        return True

    @classmethod
    def _build_transactions_fiat_price_lookup(cls) -> None:
        MAIN_LOGGER.info("Building fiat price lookup directory...")

        total_tokens = len(DexPriceManager._TX_LOOKUP)
        for i, (harmony_token, token_properties) in enumerate(
            DexPriceManager._TX_LOOKUP.items(), start=1
        ):
            d_idx = 0
            ts: Dict = {}

            while not DexPriceManager._is_valid_price_timeseries(ts):
                dex = DexPriceManager._DEX_GRAPHS[d_idx]

                # try to get token information from any dex we can until we get useful
                # data back
                if harmony_token.is_lp_token:
                    MAIN_LOGGER.info(
                        "Looking up prices for LP token: %s (%s/%s) in dex: %s...",
                        harmony_token,
                        i,
                        total_tokens,
                        dex,
                    )
                    ts = DexPriceManager._try_to_get_lp_prices_from_dexes(
                        dex,
                        harmony_token.address.eth,
                        int(token_properties["timestamp_range"]["min"]),
                        int(token_properties["timestamp_range"]["max"]),
                        token_properties["blocks"],
                    )
                else:
                    MAIN_LOGGER.info(
                        "Looking up prices for ERC20 token: %s (%s/%s) in dex: %s...",
                        harmony_token,
                        i,
                        total_tokens,
                        dex,
                    )
                    ts, failure = DexPriceManager._try_to_get_token_prices_from_dexes(
                        dex,
                        harmony_token.address.eth,
                        token_properties["blocks"],
                    )

                    if failure:
                        MAIN_LOGGER.info(
                            make_yellow(
                                "\tNo prices found for token: %s from %s",
                            ),
                            harmony_token,
                            dex,
                        )
                    else:
                        MAIN_LOGGER.info(
                            "\tSuccessfully got prices for token: %s from %s",
                            harmony_token,
                            dex,
                        )

                token_properties["fiat_prices_by_block"] = ts
                d_idx += 1

    @staticmethod
    def _try_to_get_token_prices_from_dexes(
        dex_graph: UniswapV2ForkGraph, token_address: str, blocks: Iterable[int]
    ) -> Tuple[Dict, bool]:
        return dex_graph.get_token_price_by_block_timeseries(
            token_address,
            blocks,
        )

    @staticmethod
    def _try_to_get_lp_prices_from_dexes(
        dex_graph: UniswapV2ForkGraph,
        token_address: str,
        min_ts: int,
        max_ts: int,
        blocks: Iterable[int],
    ) -> Dict:
        return dex_graph.get_lp_token_price_by_block_timeseries(
            token_address,
            min_ts,
            max_ts,
            blocks,
        )

    @staticmethod
    def _is_valid_price_timeseries(ts: Dict) -> bool:
        return bool(ts)


class HarmonyToken:  # pylint: disable=R0902
    NATIVE_TOKEN_SYMBOL = "ONE"

    NATIVE_TOKEN_ETH_ADDRESS_STR = "0xcF664087a5bB0237a0BAd6742852ec6c8d69A27a"
    _TOKEN_DIRECTORY: Dict[HarmonyAddress, HarmonyToken] = {}
    _CONV_BTC_ADDRS = {
        "0x3095c7557bCb296ccc6e363DE01b760bA031F2d9",
        "0xdc54046c0451f9269FEe1840aeC808D36015697d",
    }
    _CONV_DFK_GOLD_ADDRS = {
        "0x3a4EDcf3312f44EF027acfd8c21382a5259936e7",
        "0x576C260513204392F0eC0bc865450872025CB1cA",
    }
    _CONV_STABLE_COIN_ADDRS = {
        "0x985458E523dB3d53125813eD68c274899e9DfAb4",
        "0x3C2B8Be99c50593081EAA2A724F0B8285F5aba8f",
        "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",
    }

    def __init__(
        self,
        address: Union[str, HarmonyAddress],
        merge_one_wone_names: Optional[bool] = True,
    ):
        self.address = HarmonyAddress.get_harmony_address(address)
        self.address.belongs_to_token = True

        symbol, decimals, name = HarmonyAPI.get_token_info(self.address.eth)
        self.name = name
        self.symbol = symbol
        self.decimals = decimals

        self._conversion_unit = self._get_conversion_unit()

        # DEX stuff
        self.is_lp_token = False
        self.lp_token_0: Union[HarmonyToken, None] = None
        self.lp_token_1: Union[HarmonyToken, None] = None

        if self.symbol == "WONE":
            # consider WONE and ONE equivalent by symbol
            if merge_one_wone_names:
                self.symbol = self.NATIVE_TOKEN_SYMBOL
        else:
            # if not a native currency, try to see if it an LP position
            self._set_is_lp_token_guess()

        # add self to directory for later
        HarmonyToken._TOKEN_DIRECTORY[self.address] = self

    @classmethod
    def native_token(cls) -> HarmonyToken:
        return cls.get_harmony_token_by_address(cls.NATIVE_TOKEN_ETH_ADDRESS_STR)

    @property
    def is_native_token(self) -> bool:
        return self.address.eth == self.NATIVE_TOKEN_ETH_ADDRESS_STR

    def _set_is_lp_token_guess(self) -> None:
        dex_info = DexPriceManager.get_token_or_pair_info(self.address.eth)

        if not dex_info:
            # cannot get API response - guess based on the name
            # can't retrieve pairs this way though
            self.is_lp_token = "lp token" in self.name.lower()
        else:
            pair_info = dex_info["pair"]
            tokn_info = dex_info["token"]

            self.is_lp_token = self._is_pair(pair_info, tokn_info)

            if self.is_lp_token:
                self.lp_token_0 = HarmonyToken.get_harmony_token_by_address(
                    pair_info["token0"]["id"]
                )
                self.lp_token_1 = HarmonyToken.get_harmony_token_by_address(
                    pair_info["token1"]["id"]
                )

    @staticmethod
    def _is_pair(pair_info, token_info) -> bool:
        if bool(pair_info) ^ bool(token_info):
            # if there is only 1 result given the address
            return bool(pair_info)

        # we got an answer back for both a token and an LP pair at the same address
        # this is rare but can happen
        token_trade_vol_usd = token_info["tradeVolumeUSD"]
        token_tx_count = token_info["txCount"]
        token_total_liquidity = token_info["totalLiquidity"]
        if (
            token_trade_vol_usd < 1
            and token_total_liquidity < 10
            and token_tx_count < 100
        ):
            # somewhat hacky solution but check if the single token has unusually
            # low activity. Someone may have created this by mistake, in which
            # case we should prefer the pair's info
            return True

        # this looks more like a token than an LP position
        # haven't seen this happen yet
        return False  # pragma: no cover

    def _get_conversion_unit(self) -> str:
        if self.address.eth in self._CONV_BTC_ADDRS:  # pragma: no cover
            return "btc"
        if self.address.eth in self._CONV_DFK_GOLD_ADDRS:  # pragma: no cover
            return "kwei"
        if self.address.eth in self._CONV_STABLE_COIN_ADDRS:
            return "mwei"
        return "ether"

    def get_value_from_wei(self, amount: int) -> Decimal:
        # Simple way to determine conversion, maybe change to lookup on chain later
        # w3.fromWei doesn't seem to have an 8 decimal option for BTC
        return (
            amount / Decimal(100000000)
            if self._conversion_unit == "btc"
            else Decimal(Web3.fromWei(amount, self._conversion_unit))
        )

    @property
    def universal_symbol(self) -> str:
        # many harmony tokens start with a "1", e.g. 1USDC, 1ETH, 1BTC, 1USDT
        return self.symbol[1:] if self.symbol.startswith("1") else self.symbol

    @classmethod
    def get_harmony_token_by_address(
        cls,
        address: Union[HarmonyAddress, str],
        merge_one_wone_names: Optional[bool] = True,
    ) -> HarmonyToken:
        addr_obj = HarmonyAddress.get_harmony_address(address, merge_one_wone_names)

        if not HarmonyAPI.address_belongs_to_erc_20_token(addr_obj.eth):
            raise ValueError(
                f"This address does not appear to belong to an ERC/HRC20 token. "
                f"Got address: {address}"
            )

        return HarmonyToken._TOKEN_DIRECTORY.get(addr_obj) or HarmonyToken(
            addr_obj,
            merge_one_wone_names,
        )

    def __str__(self) -> str:  # pragma: no cover
        return "HarmonyToken: {0} ({1}) [{2}]".format(
            self.symbol, self.name, self.address.eth
        )

    def __eq__(self, other) -> bool:
        return isinstance(other, HarmonyToken) and self.address == other.address

    def __hash__(self):
        return hash("harmony_token" + str(self.address.__hash__()))


class HarmonyEVMTransaction:  # pylint: disable=R0902
    EXPLORER_TX_URL = "https://explorer.harmony.one/tx/{0}"

    def __init__(self, account: Union[HarmonyAddress, str], tx_hash: HexStr):
        # identifiers
        self.txHash = tx_hash
        self.account = HarmonyAddress.get_harmony_address(account)

        # (placeholder values)
        # token sent in this tx (outgoing)
        self.sentAmount = 0
        self.sentCurrencySymbol = ""

        # token received in this tx (incoming)
        self.gotAmount = 0
        self.gotCurrencySymbol = ""

        # get transaction data
        self.result = HarmonyAPI.get_transaction(tx_hash)
        self.to_addr = HarmonyAddress.get_harmony_address(self.result["to"])
        self.from_addr = HarmonyAddress.get_harmony_address(self.result["from"])

        # temporal data
        self.block = self.result["blockNumber"]
        self.timestamp = HarmonyEVMTransaction.get_timestamp(self.block)
        self.block_date = date.fromtimestamp(self.timestamp)

        # event data
        self.action = ""
        self.event = ""
        self.is_token_transfer = False

        # function argument data
        self.contract_pointer = (
            HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(
                self.result["to"]
            )
        )
        self.tx_payload = self.contract_pointer.decode_input(self.result["input"])

        # currency data
        self.value = Web3.fromWei(self.result["value"], "ether")
        self.coinAmount = self.value

        # assume it is ONE unless otherwise specified, inheritors of this class can change
        # this based data relevant to what they do
        self.coinType: HarmonyToken = HarmonyToken.native_token()

        self.receipt = HarmonyEVMTransaction.get_tx_receipt(tx_hash)
        self.tx_fee_in_native_token = Decimal(
            Web3.fromWei(self.result["gasPrice"], "ether") * self.receipt["gasUsed"]
        )

        self.fiatValue = 0
        self.fiatFeeValue = 0
        self.fiatType = "usd"

    @property
    def explorer_url(self):
        return self.EXPLORER_TX_URL.format(self.txHash)

    def get_fiat_value(self, exclude_fee: Optional[bool] = False) -> Decimal:
        token_price = DexPriceManager.get_price_of_token_at_block(
            self.coinType, self.block
        )
        token_qty = self.value

        fee_price = DexPriceManager.get_price_of_token_at_block(
            HarmonyToken.native_token(), self.block
        )
        fee_qty = self.tx_fee_in_native_token

        fee_val = Decimal(0) if exclude_fee else fee_price * fee_qty
        token_val = token_qty * token_price

        return fee_val + token_val

    @classmethod
    def get_timestamp(cls, block) -> int:
        return HarmonyAPI.get_timestamp(block)

    @classmethod
    def get_tx_receipt(cls, tx_hash: HexStr) -> TxReceipt:
        return HarmonyAPI.get_tx_receipt(tx_hash)

    def get_tx_function_signature(self) -> str:
        decode_successful, function_info = self.tx_payload
        if decode_successful and function_info:
            f, _ = function_info

            # escape and strip class name in python to string
            return "{0}".format(str(f)[1:-1].split(" ")[1])

        return ""


T_DECODED_ETH_SIG = Tuple[ContractFunction, Dict[str, Any]]


class HarmonyEVMSmartContract:
    POSSIBLE_ABIS = ["ERC20", "ERC721", "UniswapV2Router02", "USD Coin", "Wrapped ONE"]

    @classmethod
    @lru_cache(maxsize=256)
    def lookup_harmony_smart_contract_by_address(
        cls, address: str, name: str = ""
    ) -> HarmonyEVMSmartContract:
        return HarmonyEVMSmartContract(address, name)

    def __init__(self, address: str, assigned_name: str):
        self.address = address
        self.name = assigned_name

        # contract function requires us to know interface of source
        self.code = HarmonyAPI.get_code(address)
        self.has_code = not self._is_missing(self.code)
        self.abi = (
            self.code["abi"] if self.has_code else get_local_abi(self.POSSIBLE_ABIS[0])
        )
        self.abi_attempt_idx = 1
        self.contract = HarmonyAPI.get_contract(self.address, self.abi)

    def decode_input(
        self, tx_input: HexStr
    ) -> Tuple[bool, Union[T_DECODED_ETH_SIG, None]]:
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
    def _is_missing(code: Dict) -> bool:
        return code.get("message") in HarmonyAPI.API_NOT_FOUND_MESSAGES
