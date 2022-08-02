import pytest  # noqa
from txtool.harmony import DexPriceManager
from txtool.transactions import WalletActivity
from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_token_tx_with_intermediate_transfers():
    # random TX from explorer
    # SWAP: 31.0385 ONE -> 7.3554 USDC (de-pegged)
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    wallet_address = "0x974190a07ff72043bdeaa1f6bfe90bdd33172e51"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        wallet_address, tx_hash, exclude_intermediate_tx=False
    )

    assert len(txs) == 5

    root = txs[0]
    it_0 = txs[1]
    it_1 = txs[2]
    it_2 = txs[3]
    leaf = txs[4]

    assert root.coin_type.is_native_token
    assert root.coin_amount == 0
    assert root.tx_fee_in_native_token > 0
    assert root.is_sender
    assert not root.is_receiver
    assert not root.is_token_transfer
    assert root.to_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"

    assert float(it_0.coin_amount) == 31.03846109621060256
    assert it_0.coin_type.is_native_token
    assert it_0.is_token_transfer
    assert not it_0.is_receiver
    assert not it_0.is_sender
    assert it_0.from_addr.eth == "0x670240Cd8f514EBaD7e375EcBa7e9e6b761e893A"
    assert it_0.from_addr.token.name == "FarmersOnly LP Token"
    assert it_0.to_addr.eth == "0xF170016d63fb89e1d559e8F87a17BCC8B7CD9c00"
    assert it_0.to_addr.token.name == "Venom LP Token"
    assert it_0.from_addr.belongs_to_token

    assert float(it_1.coin_amount) == 16.260903347728752291
    assert it_1.coin_type.symbol == "FOX"
    assert it_1.is_token_transfer
    assert not it_1.is_receiver
    assert not it_1.is_sender
    assert it_1.from_addr.eth == "0xe83eE2547613327300732D9B35238A6bCf168B21"
    assert it_1.from_addr.token.name == "FarmersOnly LP Token"
    assert it_1.to_addr.eth == "0x670240Cd8f514EBaD7e375EcBa7e9e6b761e893A"
    assert it_1.to_addr.token.name == "FarmersOnly LP Token"

    assert float(it_2.coin_amount) == 7.34645
    assert it_2.coin_type.symbol == "1USDC"
    assert it_2.coin_type.universal_symbol == "USDC"
    assert it_2.is_token_transfer
    assert not it_2.is_receiver
    assert not it_2.is_sender
    assert it_2.from_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert it_2.from_addr.belongs_to_non_token_smart_contract
    assert it_2.to_addr.eth == "0xe83eE2547613327300732D9B35238A6bCf168B21"
    assert it_2.to_addr.token.name == "FarmersOnly LP Token"

    # ultimate destination is another LP token on a different DEX
    assert float(leaf.coin_amount) == 7.355363
    assert leaf.coin_type.symbol == "1USDC"
    assert leaf.coin_type.universal_symbol == "USDC"
    assert not leaf.coin_type.is_lp_token
    assert leaf.is_token_transfer
    assert not leaf.is_sender
    assert not leaf.is_receiver
    assert leaf.from_addr.eth == "0xF170016d63fb89e1d559e8F87a17BCC8B7CD9c00"
    assert leaf.from_addr.belongs_to_token
    assert leaf.from_addr.token.name == "Venom LP Token"
    assert leaf.to_addr.eth == "0x060B9A5c8e9E84b9b8034362f982dCaC289F3bFb"
    assert leaf.to_addr.belongs_to_non_token_smart_contract

    # this is the last TX, it reaches the target address
    # after a few hops
    # the block explorer actually displays this out of order...
    assert leaf.to_addr == root.to_addr


@vcr.use_cassette()
def test_token_tx_ignore_intermediate_transfers():
    # random TX from explorers
    # SWAP: 31.0385 ONE -> 7.3554 USDC (de-pegged)
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    wallet_address = "0x974190a07ff72043bdeaa1f6bfe90bdd33172e51"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        wallet_address, tx_hash, exclude_intermediate_tx=True
    )

    assert len(txs) == 2

    root = txs[0]
    leaf = txs[1]

    assert root.coin_type.is_native_token
    assert root.coin_amount == 0
    assert root.tx_fee_in_native_token > 0
    assert root.is_sender

    assert float(leaf.coin_amount) == 7.355363
    assert leaf.coin_type.symbol == "1USDC"
    assert leaf.to_addr.belongs_to_non_token_smart_contract
    assert leaf.to_addr == root.to_addr

    # from unknown contract so can't decode its signature
    assert (False, None) == root.tx_payload
    assert "" == root.get_tx_function_signature()


@vcr.use_cassette()
def test_build_prices_for_null_coin_type():
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    address = "0x974190a07ff72043bdeaa1f6bfe90bdd33172e51"

    with pytest.raises(ValueError) as e:
        txs = WalletActivity.extract_all_wallet_activity_from_transaction(
            address, tx_hash, exclude_intermediate_tx=False
        )
        for tx in txs:
            # remove coin type
            tx.coin_type = None

        DexPriceManager.initialize_static_price_manager(txs)

    assert "null coin type" in str(e)
