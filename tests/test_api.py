import pytest  # noqa
from eth_typing import HexStr

from txtool.harmony import HarmonyAPI
from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_bad_block_timestamp():
    assert 1561736306 == HarmonyAPI.get_timestamp(1)

    with pytest.raises(ValueError) as e:
        HarmonyAPI.get_timestamp(-10)
    assert "at least 1" in str(e)

    with pytest.raises(ValueError) as e:
        HarmonyAPI.get_timestamp(10000000000000)
    assert "may not exist" in str(e)


@vcr.use_cassette()
def test_bad_tx_hash_receipt():
    with pytest.raises(ValueError):
        HarmonyAPI.get_tx_receipt(HexStr("123"))
