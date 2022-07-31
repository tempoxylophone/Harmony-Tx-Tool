from __future__ import annotations
from typing import List, Dict, Union, Tuple, Iterable, TypedDict, Optional
from decimal import Decimal
from collections import defaultdict

from txtool.utils import MAIN_LOGGER, make_yellow
from txtool.dex import UniswapV2ForkGraph

from .constants import (
    NATIVE_TOKEN_ETH_ADDRESS_STR,
    NATIVE_TOKEN_SYMBOL,
)
from .api import HarmonyAPI
from .address import HarmonyAddress
from .abc import Token, Transaction


class DexPriceManager:
    class DexPriceInfo(TypedDict):
        blocks: List[int]
        timestamps: List[int]
        timestamp_range: Dict[str, Union[float, int]]
        fiat_prices_by_block: Dict[int, Decimal]

    _TX_LOOKUP: Dict[Token, DexPriceInfo] = defaultdict(
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
        transactions: Iterable[Transaction],
    ) -> None:
        DexPriceManager._build_transactions_directory(transactions)
        DexPriceManager._build_transactions_fiat_price_lookup()

    @staticmethod
    def _build_transactions_directory(
        transactions: Iterable[Transaction],
    ) -> None:
        for t in transactions:
            if not t.coin_type:
                # token is undefined or not set
                raise ValueError(
                    f"Transaction {t} has a null coin type! Can't build prices map."
                )

            # ensure ONE is included for this block so we can look up gas
            native_token: List[Token] = (
                not (t.coin_type and t.coin_type.is_native_token)
                and [t.coin_type.get_native_token()]
                or []
            )
            tokens = [t.coin_type] + native_token

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


class HarmonyToken(Token):  # pylint: disable=R0902
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
        super().__init__(address)
        self.address = HarmonyAddress.get_harmony_address(address)
        self.address.belongs_to_token = True
        self.address.token = self

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
                self.symbol = NATIVE_TOKEN_SYMBOL
        else:
            # if not a native currency, try to see if it an LP position
            self._set_is_lp_token_guess()

        # add self to directory for later
        HarmonyToken._TOKEN_DIRECTORY[self.address] = self

    @classmethod
    def get_native_token(cls) -> HarmonyToken:
        return cls.get_harmony_token_by_address(NATIVE_TOKEN_ETH_ADDRESS_STR)

    @property
    def is_native_token(self) -> bool:
        return self.address.eth == NATIVE_TOKEN_ETH_ADDRESS_STR

    @classmethod
    def get_address_and_set_token(cls, eth_address_str: str) -> HarmonyAddress:
        addr_obj = HarmonyAddress.get_harmony_address(eth_address_str)
        if addr_obj.belongs_to_token:
            token = HarmonyToken.get_harmony_token_by_address(addr_obj)
            addr_obj.token = token

        return addr_obj

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
    def _is_pair(pair_info: Dict, token_info: Dict) -> bool:
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
        return HarmonyAPI.get_value_from_wei(amount, self._conversion_unit)

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
        addr_obj = HarmonyAddress.get_harmony_address(address)

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

    def __hash__(self) -> int:
        return hash("harmony_token" + str(self.address.__hash__()))
