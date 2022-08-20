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


@vcr.use_cassette()
def test_get_tx_receipt_for_vcr_1():
    # random TX from explorer
    x = HarmonyAPI.get_tx_receipt(
        HexStr("0x2d4bf0e67024da714bce338243a0a4b49164131e6c4c832cc07fcba46848f344")
    )
    assert isinstance(dict(x), dict)
    assert 30304957 == x["blockNumber"]
    assert "0xE1Ec7223E84f065FE16Df11EE522BCe2FC8700ED" == x["from"]
    assert len(x["logs"]) == 12


@vcr.use_cassette()
def test_get_tx_receipt_for_vcr_2():
    # random TX from explorer
    x = HarmonyAPI.get_tx_receipt(
        HexStr("0x0d481f65b1b8084bfd246401f6787dba6e50a5d38f3bf57541c031262fab4be8")
    )
    assert isinstance(dict(x), dict)
    assert 30305070 == x["blockNumber"]
    assert "0x3369Cf3fFe91fD05Be6a62e92B13adf5ef7188a1" == x["from"]
    assert len(x["logs"]) == 70


@vcr.use_cassette()
def test_belongs_to_contract_for_vcr_1():
    assert HarmonyAPI.address_belongs_to_smart_contract(
        "0xcF664087a5bB0237a0BAd6742852ec6c8d69A27a"
    )


@vcr.use_cassette()
def test_belongs_to_contract_for_vcr_2():
    assert HarmonyAPI.address_belongs_to_smart_contract(
        "0xFFab183292D95A40BC6217aeFE3Cf672418b6E62"
    )
