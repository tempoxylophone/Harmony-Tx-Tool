from typing import Dict, Sequence, List
from eth_typing import HexStr

from txtool import transactions as records
from .harmony import HarmonyAPI, HarmonyEVMTransaction
from .dfk.constants import DFK_EVENT_WORDS


def get_new_events_map() -> Dict:
    return {
        'tavern': [],
        'swaps': [],
        'liquidity': [],
        'wallet': [],
        'bank': [],
        'gardens': [],
        'quests': [],
        'alchemist': [],
        'airdrops': [],
        'lending': [],
    }


def get_events(tx_hashes_strings: List[HexStr], wallet_address: str) -> Sequence[HarmonyEVMTransaction]:
    events = []

    for tx_hash_string in tx_hashes_strings:
        result = HarmonyAPI.get_transaction(tx_hash_string)
        action = HarmonyEVMTransaction.lookup_event(
            result['from'],
            result['to'],
            wallet_address
        )
        if action in DFK_EVENT_WORDS:
            # skip dfk-specific stuff for now
            continue

        receipt = HarmonyAPI.get_tx_receipt(tx_hash_string)

        if receipt['status'] != 1:
            # in progress?
            continue

        # token transfers and fees associated with them
        results = (
            records.WalletActivity.extract_all_wallet_activity_from_transaction(
                wallet_address, tx_hash_string
            )
        )
        events += results

    return events
