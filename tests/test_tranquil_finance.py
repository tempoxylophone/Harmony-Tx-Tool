from decimal import Decimal

from txtool.harmony import HarmonyAddress
from txtool.koinly import get_label_for_tx_and_description, KoinlyLabel
from txtool.activity import get_interpreted_transactions

from txtool.koinly.ruleset.constants import (
    TRANQUIL_FINANCE_COMPTROLLER_CONTRACT_ADDRESS_STR,
)

from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_consolidate_tranquil_multi_rewards_deposit() -> None:
    # random tx from explorer
    tx_hash = "0x15e02d4af324d81a5b61899662a5c88ef30f3f42c4a38e9522fdbcfe57ceeb55"
    account = HarmonyAddress.get_harmony_address_by_string(
        "0xb3439976446c7237E4Aa49b7ED63277564DFE6A1"
    )
    txs = get_interpreted_transactions(account, tx_hash)

    # should 'compress' them into 1 reward transaction
    assert len(txs) == 2

    reward_tx = txs[1]

    assert reward_tx.got_currency and reward_tx.got_currency.symbol == "TRANQ"
    assert reward_tx.got_amount == Decimal("8.139094828881237836")
    assert reward_tx.method == "claimReward(uint8,address)"

    assert reward_tx.from_addr_str == TRANQUIL_FINANCE_COMPTROLLER_CONTRACT_ADDRESS_STR
    assert reward_tx.to_addr.eth == account.eth

    label, desc = get_label_for_tx_and_description(reward_tx)

    assert label == KoinlyLabel.REWARD
    assert desc == "Claim TRANQ reward"
