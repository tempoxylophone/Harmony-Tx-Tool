from decimal import Decimal

from txtool.koinly import get_label_for_tx_and_description, KoinlyLabel
from txtool.transactions import WalletActivity

from txtool.koinly.ruleset.constants import (
    TRANQUIL_FINANCE_COMPTROLLER_CONTRACT_ADDRESS_STR,
)

from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_consolidate_tranquil_multi_rewards_deposit():
    # random tx from explorer
    tx_hash = "0x15e02d4af324d81a5b61899662a5c88ef30f3f42c4a38e9522fdbcfe57ceeb55"
    caller_address = "0xb3439976446c7237E4Aa49b7ED63277564DFE6A1"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        tx_hash, exclude_intermediate_tx=True
    )

    # should 'compress' them into 1 reward transaction
    assert len(txs) == 2

    reward_tx = txs[1]

    assert reward_tx.got_currency and reward_tx.got_currency.symbol == "TRANQ"
    assert reward_tx.got_amount == Decimal("8.139094828881237836")
    assert reward_tx.method == "claimReward(uint8,address)"

    assert reward_tx.from_addr_str == TRANQUIL_FINANCE_COMPTROLLER_CONTRACT_ADDRESS_STR
    assert reward_tx.to_addr.eth == caller_address

    label, desc = get_label_for_tx_and_description(reward_tx)

    assert label == KoinlyLabel.REWARD
    assert desc == "Claim TRANQ reward"
