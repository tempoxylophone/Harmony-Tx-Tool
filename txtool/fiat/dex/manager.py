from __future__ import annotations
from typing import List, Dict, Union, Tuple, Iterable, TypedDict, Optional
from decimal import Decimal
from collections import defaultdict

from txtool.utils import MAIN_LOGGER, make_yellow
from txtool.dex import UniswapV2ForkGraph
from txtool.harmony.constants import VIPERSWAP_GRAPH_CONFIG
from txtool.harmony import WalletActivity, HarmonyToken, Token


class DexPriceInfo(TypedDict):
    blocks: List[int]
    timestamps: List[int]
    timestamp_max: Union[float, int]
    timestamp_min: Union[float, int]
    fiat_prices_by_block: Dict[int, Decimal]


class DexPriceLookupBounds(TypedDict):
    blocks: List[int]
    timestamps: List[int]
    timestamp_max: Union[float, int]
    timestamp_min: Union[float, int]


T_DEX_PRICES = Dict[Token, DexPriceInfo]


class DexPriceManager:
    _DEX_GRAPH_URLS = [
        # order matters, attempts for lookups made first at the front
        VIPERSWAP_GRAPH_CONFIG,
    ]

    _DEX_GRAPHS = [UniswapV2ForkGraph(*x) for x in _DEX_GRAPH_URLS]

    @classmethod
    def get_price_of_token_at_block(
        cls, token: Token, block: int, price_data: T_DEX_PRICES
    ) -> Decimal:
        try:
            return price_data[token]["fiat_prices_by_block"][block]
        except KeyError:  # pragma: no cover
            MAIN_LOGGER.info(
                make_yellow("\tCouldn't find price of token: %s, %s at block = %s"),
                str(token),
                token.symbol,
                str(block),
            )
            return Decimal(0)

    @classmethod
    def get_tx_fiat_value(
        cls,
        tx: WalletActivity,
        price_data: Dict,
        exclude_fee: Optional[bool] = False,
    ) -> Decimal:
        amount_val = tx.coin_amount * cls.get_price_of_token_at_block(
            tx.coin_type, tx.block, price_data
        )

        fee_val = (
            Decimal(0)
            if exclude_fee
            else tx.tx_fee_in_native_token
            * cls.get_price_of_token_at_block(
                HarmonyToken.get_native_token(), tx.block, price_data
            )
        )

        return amount_val + fee_val

    @classmethod
    def get_price_data(
        cls,
        transactions: Iterable,
    ) -> T_DEX_PRICES:
        return cls._build_transactions_fiat_price_lookup(
            cls._get_tx_lookup(transactions)
        )

    @staticmethod
    def _get_tx_lookup(
        transactions: Iterable[WalletActivity],
    ) -> Dict:
        tx_lookup: Dict[HarmonyToken, DexPriceLookupBounds] = defaultdict(
            lambda: {
                "blocks": [],
                "timestamps": [],
                "timestamp_max": float("-inf"),
                "timestamp_min": float("+inf"),
            }
        )

        for t in transactions:
            for token in t.get_relevant_tokens():
                timestamp = t.timestamp
                p = tx_lookup[token]
                p["blocks"].append(t.block)
                p["timestamps"].append(timestamp)
                p["timestamp_max"] = max(p["timestamp_max"], timestamp)
                p["timestamp_min"] = min(p["timestamp_min"], timestamp)

        return tx_lookup

    @classmethod
    def _build_transactions_fiat_price_lookup(cls, tx_lookup: Dict) -> T_DEX_PRICES:
        MAIN_LOGGER.info("Building fiat price lookup directory...")

        total_tokens = len(tx_lookup)
        for i, (harmony_token, token_properties) in enumerate(
            tx_lookup.items(), start=1
        ):
            d_idx = 0
            ts: Dict = {}

            while not DexPriceManager._is_valid_price_timeseries(ts) and d_idx < len(
                DexPriceManager._DEX_GRAPHS
            ):
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
                        int(token_properties["timestamp_min"]),
                        int(token_properties["timestamp_max"]),
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

                    if failure:  # pragma: no cover
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

        return tx_lookup

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
