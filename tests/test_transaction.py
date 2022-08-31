from typing import Any
from datetime import datetime
from decimal import Decimal
from copy import deepcopy, copy

import pytest  # noqa
from txtool.activity.interpreter import get_interpreted_transactions
from txtool.harmony import HarmonyAddress, WalletActivity
from .utils import get_vcr

vcr = get_vcr(__file__)

TX_RANDOM_HASH = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
TX_RANDOM_ACCOUNT = HarmonyAddress.get_harmony_address_by_string(
    "0x974190a07FF72043BDEAa1f6BFe90BDd33172E51"
)

TX_RANDOM_HASH_2 = "0xaa5308615087d52a0fa17925792af3be8eb35de017fc727a0dce2854bd9b32c0"
TX_RANDOM_ACCOUNT_2 = HarmonyAddress.get_harmony_address_by_string(
    "0x9bC54Db115f9a362B5E6b9eFfcaf9c7c2486Bf16"
)


@vcr.use_cassette()
def test_token_tx_with_intermediate_transfers() -> None:
    # random TX from explorer
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        TX_RANDOM_ACCOUNT, TX_RANDOM_HASH
    )

    # transaction order is different from what is displayed in explorer for some reason
    # but all that matters is the log index that we get from blockchain
    assert len(txs) == 5

    tx = txs[0]
    assert tx.coin_type.is_native_token
    assert tx.coin_type_symbol == "ONE"
    assert tx.coin_amount == 0
    assert tx.tx_fee_in_native_token == Decimal("0.02801725940965296")
    assert tx.is_sender
    assert not tx.is_receiver
    assert not tx.is_token_transfer
    assert tx.to_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert tx.log_idx == 0

    tx = txs[1]
    assert tx.coin_amount == Decimal("7.355363")
    assert tx.coin_type.symbol == "1USDC"
    assert tx.coin_type.universal_symbol == "USDC"
    assert tx.is_token_transfer
    assert not tx.is_receiver
    assert not tx.is_sender
    assert tx.from_addr.eth == "0xF170016d63fb89e1d559e8F87a17BCC8B7CD9c00"
    assert tx.to_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert tx.log_idx == 21

    tx = txs[2]
    assert tx.coin_amount == Decimal("7.34645")
    assert tx.coin_type.symbol == "1USDC"
    assert tx.coin_type.universal_symbol == "USDC"
    assert not tx.coin_type.is_lp_token
    assert tx.is_token_transfer
    assert not tx.is_sender
    assert not tx.is_receiver
    assert tx.from_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert tx.to_addr.eth == "0xe83eE2547613327300732D9B35238A6bCf168B21"
    assert tx.log_idx == 22

    tx = txs[3]
    assert tx.coin_amount == Decimal("16.260903347728752291")
    assert tx.coin_type.symbol == "FOX"
    assert tx.is_token_transfer
    assert not tx.is_receiver
    assert not tx.is_sender
    assert tx.from_addr.eth == "0xe83eE2547613327300732D9B35238A6bCf168B21"
    assert tx.to_addr.eth == "0x670240Cd8f514EBaD7e375EcBa7e9e6b761e893A"
    assert tx.log_idx == 23

    tx = txs[4]
    assert tx.coin_type_symbol == "ONE"
    assert tx.coin_amount == Decimal("31.03846109621060256")
    assert tx.coin_type.is_native_token
    assert not tx.is_receiver
    assert not tx.is_sender
    assert tx.from_addr.eth == "0x670240Cd8f514EBaD7e375EcBa7e9e6b761e893A"
    assert tx.to_addr.eth == "0xF170016d63fb89e1d559e8F87a17BCC8B7CD9c00"
    assert tx.log_idx == 26


@vcr.use_cassette()
def test_get_function_name_for_unknown_abi_in_transaction() -> None:
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        TX_RANDOM_ACCOUNT_2, TX_RANDOM_HASH_2
    )

    # check that we can get the signature even if we don't know the contract ABI
    assert all(x.method == "claimReward(uint8,address)" for x in txs)


@vcr.use_cassette()
def test_transaction_equality() -> None:
    txs_1 = WalletActivity.extract_all_wallet_activity_from_transaction(
        TX_RANDOM_ACCOUNT_2, TX_RANDOM_HASH_2
    )
    txs_2 = WalletActivity.extract_all_wallet_activity_from_transaction(
        TX_RANDOM_ACCOUNT_2, TX_RANDOM_HASH_2
    )

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
    txs = get_interpreted_transactions(TX_RANDOM_ACCOUNT, TX_RANDOM_HASH)
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


@vcr.use_cassette()
def test_wallet_shallow_copy_transaction_activity() -> None:
    txs = get_interpreted_transactions(TX_RANDOM_ACCOUNT, TX_RANDOM_HASH)
    copy_txs = [copy(x) for x in txs]

    # can 'mutate' primitive types without affecting copy but not objects
    for c in copy_txs:
        c.log_idx = -1
        c.tx_data["hello"] = "world"

    for c in txs:
        assert c.log_idx != -1
        assert "hello" in c.tx_data
