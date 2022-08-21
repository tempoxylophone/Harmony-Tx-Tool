import pytest  # noqa

from txtool.fiat.coingecko.api import get_coin_info_by_symbol, get_coingecko_chart_data
from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_get_coin_by_symbol():
    eth_info = get_coin_info_by_symbol("ETH")
    assert "ETH" == eth_info["symbol"]
    assert "279" == eth_info["internal_id"]
    assert "Ethereum" == eth_info["name"]
    assert "ethereum" == eth_info["id"]


@vcr.use_cassette()
def test_get_coin_by_symbol_no_results():
    coin_info = get_coin_info_by_symbol("3jfckadsf")
    assert {} == coin_info


@vcr.use_cassette()
def test_get_coingecko_chart_data():
    coin_info = get_coin_info_by_symbol("TRANQ")
    chart_data = get_coingecko_chart_data(coin_info, 1633082465, 1636053120)
    assert [1633086054639, 0.06529569028894078] == chart_data[0]
    assert [1636050134229, 0.3250325984291802] == chart_data[-1]
    assert 779 == len(chart_data)


@vcr.use_cassette()
def test_get_coingecko_chart_no_results():
    coin_info = get_coin_info_by_symbol("qkjfckasq")
    chart_data = get_coingecko_chart_data(coin_info, 1633082465, 1636053120)
    assert [] == chart_data
