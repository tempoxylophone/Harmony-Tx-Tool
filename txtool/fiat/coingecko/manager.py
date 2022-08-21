from __future__ import annotations
from typing import Dict, Iterable, List, TypedDict, Union
from decimal import Decimal
from collections import defaultdict

from ...harmony import HarmonyEVMTransaction, HarmonyToken
from .api import get_coingecko_chart_data_by_symbol


class CoinGeckoPriceLookupBounds(TypedDict):
    timestamps: List[int]
    timestamp_max: Union[float, int]
    timestamp_min: Union[float, int]
    fiat_prices_by_timestamp: Dict


class CoinGeckoPriceManager:
    @classmethod
    def get_price_history_for_transactions(
        cls, transactions: Iterable[HarmonyEVMTransaction]
    ) -> Dict:
        price_lookup: Dict[HarmonyToken, CoinGeckoPriceLookupBounds] = defaultdict(
            lambda: {
                "timestamps": [],
                "timestamp_max": float("-inf"),
                "timestamp_min": float("+inf"),
                "fiat_prices_by_timestamp": {},
            }
        )

        # find time bounds extremes for transactions by currency
        for t in transactions:
            if not t.coin_type:
                raise ValueError(
                    f"Transaction {t} has a null coin type! Can't build prices map."
                )

            timestamp = t.timestamp

            p = price_lookup[t.coin_type]
            p["timestamps"].append(timestamp)
            p["timestamp_max"] = max(p["timestamp_max"], timestamp)
            p["timestamp_min"] = min(p["timestamp_min"], timestamp)

        # have what we need to look it up in the API
        for token_obj, p in price_lookup.items():
            symbol = token_obj.universal_symbol

            # add price timeseries to lookup info
            full_ts = get_coingecko_chart_data_by_symbol(
                symbol,
                int(p["timestamp_min"]),
                int(p["timestamp_max"]),
            )
            p[
                "fiat_prices_by_timestamp"
            ] = cls.get_best_estimate_at_timestamp_from_coingecko_data(
                p["timestamps"], full_ts
            )

        return price_lookup

    @classmethod
    def get_best_estimate_at_timestamp_from_coingecko_data(
        cls, timestamps: List[int], full_ts: List
    ) -> Dict:
        # assuming full_ts is in order and is a list of timestamp pairs of
        # [unix_timestamp, fiat (USD) price]
        # for each given timestamp, use as key in dictionary, where value
        # is best match
        return {
            t: cls._find_best_fit_price_by_timestamp(t, full_ts) for t in timestamps
        }

    @staticmethod
    def _find_best_fit_price_by_timestamp(timestamp: int, full_ts: List) -> float:
        # binary search for closest timestamp returned from API
        lb = 0
        ub = len(full_ts) - 1
        best_fit_info = (0, float("inf"))
        while lb <= ub:
            c = (lb + ub) // 2

            block_ts, block_usd_val = full_ts[c]
            error = abs(timestamp - block_ts)
            best_fit_info = (
                (block_usd_val, error) if error < best_fit_info[1] else best_fit_info
            )

            if timestamp < block_ts:
                ub = c - 1
            elif timestamp > block_ts:
                lb = c + 1
            else:
                # exact match for price
                return block_usd_val

        closest_usd_val, _ = best_fit_info
        return closest_usd_val

    @classmethod
    def get_price_of_token_at_timestamp(
        cls, token: HarmonyToken, timestamp: int, price_data: Dict
    ) -> Decimal:
        return Decimal(price_data[token]["fiat_prices_by_timestamp"][timestamp])
