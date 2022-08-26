import pytest  # noqa

from txtool.harmony.signature import get_function_name_by_signature
from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_get_function_signature_without_abi_claim() -> None:
    func_name = get_function_name_by_signature("0x1e83409a")

    assert func_name == "claim(address)"


def test_get_function_signature_without_abi_claim_reward() -> None:
    func_name = get_function_name_by_signature("0x0952c563")

    assert func_name == "claimReward(uint8,address)"


@vcr.use_cassette()
def test_get_function_signature_bad_signature() -> None:
    func_name = get_function_name_by_signature("q38rjdkfmcakdsnfaw")

    # don't throw an error just return nothing
    assert func_name == ""

    func_name = get_function_name_by_signature("")

    assert func_name == ""

    # will actually request but still should return nothing
    func_name = get_function_name_by_signature("0123456789")

    assert func_name == ""


@vcr.use_cassette()
def test_get_function_signature() -> None:
    signature = "0xecb586a5"
    signature_name = get_function_name_by_signature(signature)
    assert signature_name == "remove_liquidity(uint256,uint256[3])"
