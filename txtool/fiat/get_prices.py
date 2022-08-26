from typing import Iterable, Dict
from decimal import Decimal
from datetime import datetime
from collections import defaultdict
from txtool.harmony import HarmonyToken, WalletActivity

from ..fiat.dex.manager import DexPriceManager
from ..fiat.coingecko.manager import CoinGeckoPriceManager

# June 23, 2022 1:30 PM UTC, Horizon Bridge began to be drained of funds
# source: https://medium.com/harmony-one/harmonys-horizon-bridge-hack-1e8d283b6d66
# https://etherscan.io/tx/0x2f259dec682ccd6517c09b771d6edb439f1925e87b562a72649a708fdd0511e1
HARMONY_HACK_DATE = datetime.fromisoformat("2022-06-23T13:30:00")
KOINLY_TRANQ_PRICE_AVAILABLE_AFTER_DATE = datetime.fromisoformat("2021-11-28T00:00:00")

T_PRICE_DATA_DICT = Dict[WalletActivity, Dict[HarmonyToken, Decimal]]


def get_token_prices_for_transactions(
    txs: Iterable[WalletActivity],
) -> T_PRICE_DATA_DICT:
    # create mapping from transaction to all relevant price data
    all_price_data: T_PRICE_DATA_DICT = defaultdict(dict)

    hack_ts = HARMONY_HACK_DATE.timestamp()
    # transactions do not have any notion of knowledge of their fiat values
    # get price of token at block & get price of token at timestamp
    # also need to account for harmony bridge hack date

    # can only use DEX prices before the hack date
    before = [
        x
        for x in txs
        if x.timestamp <= hack_ts and isinstance(x.coin_type, HarmonyToken)
    ]
    price_data_before = DexPriceManager.get_price_data(before)
    for tx in before:
        tokens = tx.get_relevant_tokens()
        for t in tokens:
            all_price_data[tx][t] = DexPriceManager.get_price_of_token_at_block(
                t, tx.block, price_data_before
            )

    # after hack, must use coingecko
    after = [
        x
        for x in txs
        if (x.timestamp > hack_ts and isinstance(x.coin_type, HarmonyToken))
        or is_coingecko_edge_case(x)
    ]
    price_data_after = CoinGeckoPriceManager.get_price_history_for_transactions(after)
    for tx in after:
        tokens = tx.get_relevant_tokens()
        for t in tokens:
            all_price_data[tx][
                t
            ] = CoinGeckoPriceManager.get_price_of_token_at_timestamp(
                t, tx.timestamp, price_data_after
            )

    # each transaction has to know the price of ONE and the price of any token it interacts with
    # at that time
    return all_price_data


def is_coingecko_edge_case(tx: WalletActivity) -> bool:
    # some tokens don't exist in the dex, but also don't exist in Koinly.
    # in those cases, we will have to look them up on coingecko
    if (
        "TRANQ" in [x.universal_symbol for x in tx.get_relevant_tokens()]
        and tx.block_date < KOINLY_TRANQ_PRICE_AVAILABLE_AFTER_DATE
    ):
        return True

    return False
