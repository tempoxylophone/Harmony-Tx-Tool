from typing import List, Dict
from decimal import Decimal
from unittest.mock import patch

from web3 import Web3
import pytest  # noqa

from txtool.dex import UniswapV2ForkGraph, DatabaseUnavailableError
from txtool.harmony import HarmonyToken, HarmonyEVMTransaction, DexPriceManager

from .utils import get_non_cost_transactions_from_txt_hash, get_vcr

vcr = get_vcr(__file__)

VIPER_SWAP = UniswapV2ForkGraph(
    "https://graph.viper.exchange/subgraphs/name/venomprotocol/venomswap-v2",
    "graph.viper.exchange",
    "https://info.viper.exchange",
)


@vcr.use_cassette()
def test_get_coin_info_graph_only():
    token_address = "0xea589e93ff18b1a1f1e9bac7ef3e86ab62addc79"
    token_info = VIPER_SWAP.get_token_or_pair_info(token_address)

    assert token_info["pair"] is None
    assert token_info["token"]["id"] == token_address
    assert token_info["token"]["name"] == "Viper"
    assert token_info["token"]["symbol"] == "VIPER"
    assert token_info["token"]["txCount"] > 3_850_000


@vcr.use_cassette()
def test_get_coin_info():
    token_address = "0xea589e93ff18b1a1f1e9bac7ef3e86ab62addc79"
    token_object = HarmonyToken(token_address)

    assert not token_object.is_lp_token
    assert token_object.address.belongs_to_token
    assert token_object.address.belongs_to_smart_contract
    assert not token_object.address.belongs_to_non_token_smart_contract
    assert not token_object.is_native_token

    # random tx from explorer
    wallet_address = "0x60b206dFD4af82FaFdbA5Af3C619D0c48129b3a1"
    tx_hash = "0x7fd33525c96258963fcfb0bba74ada0f2b52b40d01a746e9d184dda66df6b52f"
    txs = get_non_cost_transactions_from_txt_hash(wallet_address, tx_hash)

    assert len(txs) == 1

    tx: HarmonyEVMTransaction = txs[0]
    assert tx.coin_amount == 5

    token_price = DexPriceManager.get_price_of_token_at_block(tx.coin_type, tx.block)
    assert float(token_price) == 0.02140439349414948193925037049

    fiat_val = tx.get_fiat_value(exclude_fee=True)

    # test exact
    assert fiat_val == tx.coin_amount * token_price

    # test approx
    assert float(fiat_val) == 0.10702196747074741

    assert '"transfer(address,uint256)"' == tx.get_tx_function_signature()
    assert "https://explorer.harmony.one/tx/" + tx_hash == tx.explorer_url


@vcr.use_cassette()
def test_lp_token_info():
    token_address = "0xf170016d63fb89e1d559e8f87a17bcc8b7cd9c00"
    token_info = VIPER_SWAP.get_token_or_pair_info(token_address)

    assert bool(token_info["pair"])
    assert token_info["pair"]["id"] == token_address
    assert token_info["pair"]["token0"]["symbol"] == "1USDC"
    assert token_info["pair"]["token1"]["symbol"] == "WONE"
    assert (
            token_info["pair"]["token0"]["id"]
            == "0x985458e523db3d53125813ed68c274899e9dfab4"
    )
    assert (
            token_info["pair"]["token1"]["id"]
            == "0xcf664087a5bb0237a0bad6742852ec6c8d69a27a"
    )

    token_object = HarmonyToken(token_address)
    assert token_object.symbol == "VENOM-LP"
    assert token_object.name == "Venom LP Token"

    assert token_object.is_lp_token
    assert token_object.address.belongs_to_token
    assert token_object.address.belongs_to_smart_contract
    assert not token_object.address.belongs_to_non_token_smart_contract
    assert not token_object.is_native_token
    assert isinstance(token_object.lp_token_0, HarmonyToken)
    assert isinstance(token_object.lp_token_1, HarmonyToken)
    assert not token_object.lp_token_0.is_lp_token
    assert not token_object.lp_token_1.is_lp_token
    assert not token_object.lp_token_0.is_native_token
    assert token_object.lp_token_1.is_native_token
    assert token_object.lp_token_0.address.eth == Web3.toChecksumAddress(
        "0x985458e523db3d53125813ed68c274899e9dfab4"
    )
    assert token_object.lp_token_1.address.eth == Web3.toChecksumAddress(
        "0xcf664087a5bb0237a0bad6742852ec6c8d69a27a"
    )
    assert token_object.lp_token_0.symbol == "1USDC"
    assert token_object.lp_token_1.symbol == "ONE"
    assert token_object.lp_token_0.universal_symbol == "USDC"
    assert token_object.lp_token_1.universal_symbol == "ONE"

    # random tx from explorer
    wallet_address = "0x6B11C4cA9a2540F05c90655BDA08B251B29fcC79"
    tx_hash = "0xd1501298d70e47ebb086fdbe04e4143e820da2d89509bcb9325b0463bd374151"

    lp_token_address = "0xf170016d63fb89e1d559e8f87a17bcc8b7cd9c00"
    tx_block_num = 28330799

    price_query_data = VIPER_SWAP._get_graph_ql_pair_data(
        lp_token_address, 1656536345, 1656709145
    )
    price_blocks: List[Dict] = price_query_data["pair"]["liquidityPositionSnapshots"]

    price_block = price_blocks[
        VIPER_SWAP._get_best_block_idx(tx_block_num, price_blocks)
    ]

    # you can get the exact match
    assert price_block["block"] == 28330799
    assert price_block["liquidityTokenTotalSupply"] == "0.133918922586342733"
    assert price_block["reserveUSD"] == "203886.0482011466875300303857669465"

    price_per_lp_token = Decimal(price_block["reserveUSD"]) / Decimal(
        price_block["liquidityTokenTotalSupply"]
    )

    lp_price_ts = VIPER_SWAP.get_lp_token_price_by_block_timeseries(
        lp_token_address,
        min_ts=1656536345,
        max_ts=1656709145,
        block_nums=[tx_block_num],
    )

    assert lp_price_ts[price_block["block"]] == price_per_lp_token

    txs = get_non_cost_transactions_from_txt_hash(wallet_address, tx_hash)

    assert len(txs) == 1

    tx: HarmonyEVMTransaction = txs[0]
    assert float(tx.coin_amount) == 0.000057682787963833

    fiat_val_usd = tx.get_fiat_value(exclude_fee=True)

    # check exact
    assert fiat_val_usd == price_per_lp_token * tx.coin_amount

    # check approx
    assert float(fiat_val_usd) == 87.81967073837521837658654842

    # check properties
    assert '"transfer(address,uint256)"' == tx.get_tx_function_signature()
    assert "https://explorer.harmony.one/tx/" + tx_hash == tx.explorer_url


@vcr.use_cassette()
def test_get_approx_block_match_for_lp_token():
    lp_token_address = "0xf170016d63fb89e1d559e8f87a17bcc8b7cd9c00"

    price_query_data = VIPER_SWAP._get_graph_ql_pair_data(
        lp_token_address, 1656536345, 1656709145
    )
    price_blocks: List[Dict] = price_query_data["pair"]["liquidityPositionSnapshots"]

    # --- test non-exact match approximations ---
    price_block = price_blocks[VIPER_SWAP._get_best_block_idx(28370280, price_blocks)]
    assert price_block["block"] == 28370274

    price_block = price_blocks[VIPER_SWAP._get_best_block_idx(28321800, price_blocks)]
    assert price_block["block"] == 28321854

    price_block = price_blocks[VIPER_SWAP._get_best_block_idx(28322290, price_blocks)]
    assert price_block["block"] == 28322286


def test_try_to_get_unknown_lp_token_value():
    # token is unknown, can't lookup price in Uniswap Graph
    lp_token_address = "0xaD65D5fCE1D9634ca33D9dB47d2Ea7569f35e13C"

    price_query_data = VIPER_SWAP.get_lp_token_price_by_block_timeseries(
        lp_token_address, 1_577_854_800, 1_640_926_800, [28322290, 28321800, 28322290]
    )

    assert price_query_data == {}


def test_invalid_timestamp_range_request():
    with pytest.raises(ValueError) as e:
        lp_token_address = "0xf170016d63fb89e1d559e8f87a17bcc8b7cd9c00"

        VIPER_SWAP._get_graph_ql_pair_data(lp_token_address, 100, 0)

    assert "Invalid timestamp range" in str(e)


def test_dex_json_empty_exception():
    with patch("requests.Response.json") as req_mock:
        # null response
        req_mock.return_value = {}

        with pytest.raises(RuntimeError) as e:
            VIPER_SWAP.get_token_or_pair_info("")

        assert "Could not get data" in str(e)


@vcr.use_cassette()
def test_dex_database_error():
    with patch("requests.Response.json") as req_mock:
        # null response
        req_mock.return_value = {
            "errors": [{"message": "Store error: database unavailable"}]
        }

        with pytest.raises(DatabaseUnavailableError) as e:
            VIPER_SWAP.get_token_or_pair_info("")

        assert "Database unavailable" in str(e)
