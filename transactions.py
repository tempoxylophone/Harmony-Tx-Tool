#!/usr/bin/env python3
from typing import List
from pyhmy import account
import nets


def get_harmony_tx_list(address: str, page_size: int) -> List[str]:
    offset = 0
    txs = []
    has_more = True
    while has_more:
        results = account.get_transaction_history(
            address,
            page=offset,
            page_size=page_size,
            include_full_tx=False,
            endpoint=nets.hmy_main
        ) or []
        has_more = bool(results)
        offset += 1
        txs += results

    # de-dupe tx hashes in order
    return list(dict.fromkeys(txs))


def get_num_tx_for_wallet(address: str):
    return account.get_transaction_count(address, endpoint=nets.hmy_main)
