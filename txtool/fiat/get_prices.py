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
HARMONY_HACK_TS = HARMONY_HACK_DATE.timestamp()
KOINLY_TRANQ_PRICE_AVAILABLE_AFTER_DATE = datetime.fromisoformat("2021-11-28T00:00:00")

T_PRICE_DATA_DICT = Dict[WalletActivity, Dict[HarmonyToken, Decimal]]


def get_token_prices_for_transactions(
    txs: Iterable[WalletActivity],
) -> T_PRICE_DATA_DICT:
    # create mapping from transaction to all relevant price data
    all_price_data: T_PRICE_DATA_DICT = defaultdict(dict)

    # can only use DEX prices before the hack date
    before = [x for x in txs if _should_get_from_dex(x)]
    price_data_before = DexPriceManager.get_price_data(before)
    for tx in before:
        tokens = tx.get_relevant_tokens()
        for t in tokens:
            all_price_data[tx][t] = DexPriceManager.get_price_of_token_at_block(
                t, tx.block, price_data_before
            )

    # after hack, must use coingecko
    after = [x for x in txs if _should_get_from_coingecko(x)]
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


def _should_get_from_dex(tx: WalletActivity) -> bool:
    return (
        # must be before de-peg
        tx.timestamp <= HARMONY_HACK_TS
        and
        # must be a token instance, can't be placeholder
        tx.coin_type.__class__ == HarmonyToken
    )


def _should_get_from_coingecko(tx: WalletActivity) -> bool:
    return (
        # must be before de-peg
        (tx.timestamp > HARMONY_HACK_TS or _is_coingecko_edge_case(tx))
        and
        # must be token instance, can't be placeholder
        tx.coin_type.__class__ == HarmonyToken
    )


def _is_coingecko_edge_case(tx: WalletActivity) -> bool:
    # some tokens don't exist in the dex, but also don't exist in Koinly.
    # in those cases, we will have to look them up on coingecko
    if (
        "TRANQ" in [x.universal_symbol for x in tx.get_relevant_tokens()]
        and tx.block_date < KOINLY_TRANQ_PRICE_AVAILABLE_AFTER_DATE
    ):
        return True

    return False
