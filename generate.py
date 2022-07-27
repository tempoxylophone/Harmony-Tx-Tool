#!/usr/bin/env python3
"""
 Copyright 2021 Paul Willworth <ioscode@gmail.com>
"""
from typing import Dict, List
from koinly_interpreter import KoinlyInterpreter
from harmony import DexPriceManager
from transactions import WalletActivity


def get_csv(records: Dict[str, List[WalletActivity]]) -> str:
    wallet_txs = records['wallet']

    # get fiat prices
    DexPriceManager.initialize_static_price_manager(wallet_txs)

    # build CSV
    return (
            KoinlyInterpreter.get_csv_row_header() +
            "".join(tx.to_csv_row(
                KoinlyInterpreter.KOINLY_USE_ONE_ADDRESS_FORMAT
            ) for tx in wallet_txs)
    )
