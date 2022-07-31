import pytest  # noqa
from txtool.harmony import HarmonyToken
from txtool.harmony.constants import NATIVE_TOKEN_ETH_ADDRESS_STR


def test_token_object_equality():
    native_token = HarmonyToken.get_native_token()

    # should not invoke the constructor directly, but if two instances are
    # created then, they should be considered equal based on properties
    native_token_equivalent = HarmonyToken(NATIVE_TOKEN_ETH_ADDRESS_STR)

    assert native_token == native_token_equivalent


def test_merge_wone():
    native_token = HarmonyToken.get_native_token()
    wone_address = "0x005caC9eEd29CceC0F9Cca3A0A2052DeFF584667"

    assert native_token.address.eth != wone_address

    wrapped_native_token = HarmonyToken.get_harmony_token_by_address(
        wone_address,
        # keep them as separate tokens
        merge_one_wone_names=False,
    )

    # they should be different
    # as far as koinly knows, if you have the symbols be the same it is the same
    # currency, but we will always store the ONE vs WONE as different objects
    # because they have different addresses
    assert wrapped_native_token.symbol != native_token.symbol


def test_create_token_from_non_erc20_address():
    # this is a smart contract address
    # random address from explorer
    with pytest.raises(ValueError) as e:
        HarmonyToken.get_harmony_token_by_address(
            "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
        )
    assert "This address does not appear to belong to an ERC/HRC20 token" in str(e)

    # this is a wallet address
    # random address from explorer
    with pytest.raises(ValueError) as e:
        HarmonyToken.get_harmony_token_by_address(
            "0x4f480ebee194137ff245a9caad1dcc8d051a98fc"
        )
    assert "This address does not appear to belong to an ERC/HRC20 token" in str(e)


def test_create_token_from_erc20_address():
    rune_token = HarmonyToken.get_harmony_token_by_address(
        "0x66F5BfD910cd83d3766c4B39d13730C911b2D286"
    )

    assert not rune_token.is_lp_token
    assert not rune_token.is_native_token
    assert rune_token.name == "Shvas rune"
    assert rune_token.symbol == "DFKSHVAS"


def test_ambiguous_token_or_lp_position():
    dual_address = "0x0ea67cfe61d2847e1b14a374a884a35529267818"
    token = HarmonyToken.get_harmony_token_by_address(dual_address)
    assert token.is_lp_token
    assert token.lp_token_0.symbol == "JENN"
    assert token.lp_token_1.symbol == "ONE"
