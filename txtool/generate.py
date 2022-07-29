"""
 Copyright 2021 Paul Willworth <ioscode@gmail.com>
"""
from typing import Sequence
from txtool.koinly import KoinlyInterpreter, KoinlyConfig
from txtool.harmony import DexPriceManager, HarmonyAddress
from txtool.transactions import HarmonyEVMTransaction


def get_csv(events: Sequence[HarmonyEVMTransaction]) -> str:
    # get fiat prices
    DexPriceManager.initialize_static_price_manager(events)

    report_config = KoinlyConfig(
        address_format=HarmonyAddress.FORMAT_ONE,
        omit_tracked_fiat_prices=True
    )

    # build CSV
    return (
            KoinlyInterpreter.get_csv_row_header() +
            "".join(tx.to_csv_row(
                report_config
            ) for tx in events)
    )
