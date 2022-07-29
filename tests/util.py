from typing import List
from txtool.harmony import DexPriceManager
from txtool.transactions import WalletActivity
from txtool.koinly import is_cost


def get_non_cost_transactions_from_txt_hash(wallet_address: str, tx_hash: str) -> List[WalletActivity]:
    non_cost_txs = [
        x for x in WalletActivity.extract_all_wallet_activity_from_transaction(wallet_address, tx_hash)
        if not is_cost(x)
    ]

    # side effect
    DexPriceManager.initialize_static_price_manager(non_cost_txs)

    return non_cost_txs
