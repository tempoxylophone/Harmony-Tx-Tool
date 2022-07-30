import pytest  # noqa
from txtool.harmony import HarmonyAddress

TEST_ADDRESS_ETH_STR = HarmonyAddress.clean_eth_address_str(
    "0xebcd16e8c1d8f493ba04e99a56474122d81a9c58"
)
TEST_ADDRESS_ONE_STR = "one1a0x3d6xpmr6f8wsyaxd9v36pytvp48zckswvv9"


def test_convert_one_to_hex():
    assert (
        HarmonyAddress.convert_one_to_hex(TEST_ADDRESS_ONE_STR) == TEST_ADDRESS_ETH_STR
    )
    assert (
        HarmonyAddress.convert_one_to_hex(TEST_ADDRESS_ETH_STR) == TEST_ADDRESS_ETH_STR
    )


def test_convert_hex_to_one():
    assert (
        HarmonyAddress.convert_hex_to_one(TEST_ADDRESS_ETH_STR) == TEST_ADDRESS_ONE_STR
    )
    assert (
        HarmonyAddress.convert_hex_to_one(TEST_ADDRESS_ONE_STR) == TEST_ADDRESS_ONE_STR
    )


def test_address_object():
    address = HarmonyAddress.get_harmony_address(TEST_ADDRESS_ETH_STR)
    assert address.eth == TEST_ADDRESS_ETH_STR
    assert str(address) == TEST_ADDRESS_ETH_STR
    assert address.one == HarmonyAddress.convert_hex_to_one(TEST_ADDRESS_ETH_STR)
    assert HarmonyAddress.FORMAT_ONE == HarmonyAddress.get_address_string_format(
        address.one
    )
    assert HarmonyAddress.FORMAT_ETH == HarmonyAddress.get_address_string_format(
        address.eth
    )

    address_2 = HarmonyAddress.get_harmony_address(TEST_ADDRESS_ETH_STR)
    assert address is address_2

    # should be able to get address by ONE address too and get equivalent
    token_address = HarmonyAddress.get_harmony_address(TEST_ADDRESS_ONE_STR)
    assert token_address.one == TEST_ADDRESS_ONE_STR
    assert token_address.eth == HarmonyAddress.convert_one_to_hex(TEST_ADDRESS_ONE_STR)


def test_address_object_constructor_requirements():
    with pytest.raises(ValueError) as e:
        HarmonyAddress(TEST_ADDRESS_ONE_STR)
    assert "Use ETH address" in str(e)

    with pytest.raises(ValueError) as e:
        HarmonyAddress("???asdjfkasd")
    assert "Bad address" in str(e)


def test_detect_formats():
    assert HarmonyAddress.FORMAT_ETH == HarmonyAddress.get_address_string_format(
        TEST_ADDRESS_ETH_STR
    )
    assert HarmonyAddress.FORMAT_ONE == HarmonyAddress.get_address_string_format(
        TEST_ADDRESS_ONE_STR
    )

    with pytest.raises(ValueError):
        HarmonyAddress.get_address_string_format("???asdjfkasdj")
