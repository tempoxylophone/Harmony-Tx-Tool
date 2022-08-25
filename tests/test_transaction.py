from typing import Any
from datetime import datetime
from copy import deepcopy
import pytest  # noqa
from txtool.activity.interpreter import get_interpreted_transaction_from_hash
from txtool.harmony import WalletActivity
from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_token_tx_with_intermediate_transfers() -> None:
    # random TX from explorer
    # SWAP: 31.0385 ONE -> 7.3554 USDC (de-pegged)
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        tx_hash, exclude_intermediate_tx=False
    )

    assert len(txs) == 6

    root = txs[0]
    it_0 = txs[1]
    it_1 = txs[2]
    it_2 = txs[3]
    leaf = txs[4]
    get = txs[5]

    assert root.coin_type.is_native_token
    assert root.coin_amount == 0
    assert root.tx_fee_in_native_token > 0
    assert root.is_sender
    assert not root.is_receiver
    assert not root.is_token_transfer
    assert root.to_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"

    # Account sends 31 WONE to Venom LP
    assert float(it_0.coin_amount) == 31.03846109621060256
    assert it_0.coin_type.is_native_token
    assert it_0.is_token_transfer
    assert not it_0.is_receiver
    assert it_0.is_sender
    assert it_0.from_addr == root.account
    assert it_0.to_addr.eth == "0xF170016d63fb89e1d559e8F87a17BCC8B7CD9c00"
    assert it_0.to_addr.token and it_0.to_addr.token.name == "Venom LP Token"

    # Farmers Only LP sends 16 FOX to Farmers Only LP
    assert float(it_1.coin_amount) == 16.260903347728752291
    assert it_1.coin_type.symbol == "FOX"
    assert it_1.is_token_transfer
    assert not it_1.is_receiver
    assert not it_1.is_sender
    assert it_1.from_addr.eth == "0xe83eE2547613327300732D9B35238A6bCf168B21"
    assert it_1.from_addr.token and it_1.from_addr.token.name == "FarmersOnly LP Token"
    assert it_1.to_addr.eth == "0x670240Cd8f514EBaD7e375EcBa7e9e6b761e893A"
    assert it_1.to_addr.token and it_1.to_addr.token.name == "FarmersOnly LP Token"

    # Original Contract sends 7 USDC to Farmers Only LP
    assert float(it_2.coin_amount) == 7.34645
    assert it_2.coin_type.symbol == "1USDC"
    assert it_2.coin_type.universal_symbol == "USDC"
    assert it_2.is_token_transfer
    assert not it_2.is_receiver
    assert not it_2.is_sender
    assert it_2.from_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert it_2.from_addr.belongs_to_non_token_smart_contract
    assert it_2.to_addr.eth == "0xe83eE2547613327300732D9B35238A6bCf168B21"
    assert it_2.to_addr.token and it_2.to_addr.token.name == "FarmersOnly LP Token"

    # Venom LP sends 7 USDC to Original Contract
    assert float(leaf.coin_amount) == 7.355363
    assert leaf.coin_type.symbol == "1USDC"
    assert leaf.coin_type.universal_symbol == "USDC"
    assert not leaf.coin_type.is_lp_token
    assert leaf.is_token_transfer
    assert not leaf.is_sender
    assert not leaf.is_receiver
    assert leaf.from_addr.eth == "0xF170016d63fb89e1d559e8F87a17BCC8B7CD9c00"
    assert leaf.from_addr.belongs_to_token
    assert leaf.from_addr.token and leaf.from_addr.token.name == "Venom LP Token"
    assert leaf.to_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert leaf.to_addr.belongs_to_non_token_smart_contract

    # Original Contract sends you 7 USDC
    assert float(get.coin_amount) == 7.355363
    assert get.coin_type.symbol == "1USDC"
    assert get.coin_type.universal_symbol == "USDC"
    assert not get.coin_type.is_lp_token
    assert get.is_token_transfer
    assert get.from_addr == root.to_addr
    assert get.to_addr == root.account
    assert not get.to_addr.belongs_to_non_token_smart_contract

    # this is the last TX, it reaches the target address
    # after a few hops
    # the block explorer actually displays this out of order...
    assert leaf.to_addr == root.to_addr


@vcr.use_cassette()
def test_token_tx_ignore_intermediate_transfers() -> None:
    # random TX from explorers
    # SWAP: 31.0385 ONE -> 7.3554 USDC (de-pegged)
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        tx_hash, exclude_intermediate_tx=True
    )

    assert len(txs) == 3

    cost = txs[0]
    send_one = txs[1]
    get_usdc = txs[2]

    assert cost.coin_type.is_native_token
    assert cost.coin_amount == 0
    assert cost.tx_fee_in_native_token > 0
    assert cost.is_sender

    # send ONE
    assert float(send_one.coin_amount) == 31.03846109621060256
    assert send_one.coin_type.symbol == "ONE"
    assert send_one.from_addr == cost.from_addr
    assert send_one.sent_amount == send_one.coin_amount
    assert (
        send_one.sent_currency
        and send_one.sent_currency.symbol == send_one.coin_type.symbol
    )

    # get USDC
    assert float(get_usdc.coin_amount) == 7.355363
    assert get_usdc.coin_type.symbol == "1USDC"
    assert get_usdc.to_addr == cost.from_addr
    assert get_usdc.got_currency and get_usdc.got_currency.symbol == "1USDC"
    assert get_usdc.got_amount == get_usdc.coin_amount


@vcr.use_cassette()
def test_get_function_name_for_unknown_abi_in_transaction() -> None:
    tx_hash = "0xaa5308615087d52a0fa17925792af3be8eb35de017fc727a0dce2854bd9b32c0"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(tx_hash)

    # check that we can get the signature even if we don't know the contract ABI
    assert all(x.method == "claimReward(uint8,address)" for x in txs)


@vcr.use_cassette()
def test_transaction_equality() -> None:
    tx_hash = "0xaa5308615087d52a0fa17925792af3be8eb35de017fc727a0dce2854bd9b32c0"
    txs_1 = WalletActivity.extract_all_wallet_activity_from_transaction(tx_hash)
    txs_2 = WalletActivity.extract_all_wallet_activity_from_transaction(tx_hash)

    for t1, t2 in zip(txs_1, txs_2):
        assert t1 == t2
        assert id(t1) != id(t2)

    for t1, t2 in zip(txs_1, reversed(txs_2)):
        assert t1 != t2
        assert id(t1) != id(t2)

    # test non-tx object
    assert "hello" != txs_1[0]


@vcr.use_cassette()
def test_wallet_deepcopy_transaction_activity() -> None:
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    txs = get_interpreted_transaction_from_hash(tx_hash)
    copy_txs = [deepcopy(tx) for tx in txs]

    # alter the fields in tx2 unless they are objects in our package
    for tx1, tx2 in zip(txs, copy_txs):
        for attr_name, attr in tx1.__dict__.items():
            cls_module = attr.__class__.__module__.rsplit(".", 1)[0]

            if "txtool.harmony" not in cls_module:
                v: Any
                if isinstance(attr, bool):
                    v = not getattr(tx1, attr_name)
                elif isinstance(attr, datetime):
                    v = datetime.utcnow()
                elif isinstance(attr, tuple):
                    v = (1, 2)
                elif hasattr(attr, "__setitem__"):
                    v = getattr(tx2, attr_name)
                    v["test_key"] = 1
                elif attr is None:
                    v = None
                else:
                    v = getattr(tx2, attr_name) + attr.__class__(1)

                # change the value
                setattr(tx2, attr_name, v)

    # check that altering these fields has no bearing on the original variables
    # they are supposed to copy
    for tx1, tx2 in zip(txs, copy_txs):
        for attr_name, attr in tx1.__dict__.items():
            cls_module = attr.__class__.__module__.rsplit(".", 1)[0]

            if "txtool.harmony" not in cls_module:
                a = getattr(tx1, attr_name)
                b = getattr(tx2, attr_name)
                assert (a is None and b is None) or a != b
