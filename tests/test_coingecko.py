import pytest  # noqa

from txtool.harmony import HarmonyToken, HarmonyAddress

from txtool.fiat.coingecko.api import get_coin_info_by_symbol, get_coingecko_chart_data
from txtool.fiat.coingecko import CoinGeckoPriceManager
from txtool.activity.interpreter import get_interpreted_transactions

from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_get_coin_by_symbol() -> None:
    eth_info = get_coin_info_by_symbol("ETH")
    assert "ETH" == eth_info["symbol"]
    assert "279" == eth_info["internal_id"]
    assert "Ethereum" == eth_info["name"]
    assert "ethereum" == eth_info["id"]


@vcr.use_cassette()
def test_get_coin_by_symbol_no_results() -> None:
    coin_info = get_coin_info_by_symbol("3jfckadsf")
    assert {} == coin_info


@vcr.use_cassette()
def test_get_coingecko_chart_data() -> None:
    coin_info = get_coin_info_by_symbol("TRANQ")
    chart_data = get_coingecko_chart_data(coin_info, 1633082465, 1636053120)
    assert (1633086054639, 0.06529569028894078) == chart_data[0]
    assert (1636050134229, 0.3250325984291802) == chart_data[-1]
    assert 779 == len(chart_data)


@vcr.use_cassette()
def test_get_coingecko_chart_no_results() -> None:
    coin_info = get_coin_info_by_symbol("qkjfckasq")
    chart_data = get_coingecko_chart_data(coin_info, 1633082465, 1636053120)
    assert [] == chart_data


@vcr.use_cassette()
def test_get_coingecko_price_data() -> None:
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    account = HarmonyAddress.get_harmony_address_by_string(
        "0x974190a07FF72043BDEAa1f6BFe90BDd33172E51"
    )
    txs = get_interpreted_transactions(account, tx_hash)
    tx_timestamp = 1659190650
    for tx in txs:
        assert tx.timestamp == tx_timestamp

    price_history = CoinGeckoPriceManager.get_price_history_for_transactions(txs)

    token_usdc = HarmonyToken.get_harmony_token_by_address(
        "0x985458E523dB3d53125813eD68c274899e9DfAb4"
    )
    token_one = HarmonyToken.get_native_token()

    assert (
        price_history[token_usdc]["fiat_prices_by_timestamp"][tx_timestamp]
        == 1.000612752945378
    )
    assert (
        price_history[token_one]["fiat_prices_by_timestamp"][tx_timestamp]
        == 0.02401051551541988
    )
