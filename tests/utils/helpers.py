from typing import List

from txtool.transactions import WalletActivity
from txtool.koinly import is_cost


def get_non_cost_transactions_from_txt_hash(
    wallet_address: str, tx_hash: str
) -> List[WalletActivity]:
    return [
        x
        for x in WalletActivity.extract_all_wallet_activity_from_transaction(
            wallet_address, tx_hash
        )
        if not is_cost(x)
    ]
