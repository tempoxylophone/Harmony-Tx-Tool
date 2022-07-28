#!/usr/bin/env python3
"""
 Copyright 2021 Paul Willworth <ioscode@gmail.com>
"""
from typing import Dict, List
from koinly import KoinlyInterpreter, KoinlyConfig
from harmony import DexPriceManager, HarmonyAddress
from transactions import HarmonyEVMTransaction


def get_csv(records: Dict[str, List[HarmonyEVMTransaction]]) -> str:
    wallet_txs = records['wallet']

    # get fiat prices
    DexPriceManager.initialize_static_price_manager(wallet_txs)

    report_config = KoinlyConfig(
        address_format=HarmonyAddress.FORMAT_ONE,
        omit_tracked_fiat_prices=True
    )

    # build CSV
    return (
            KoinlyInterpreter.get_csv_row_header() +
            "".join(tx.to_csv_row(
                report_config
            ) for tx in wallet_txs)
    )
