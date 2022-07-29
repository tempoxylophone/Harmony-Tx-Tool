"""
 Copyright 2021 Paul Willworth <ioscode@gmail.com>
"""
from typing import Sequence
from txtool.koinly import KoinlyInterpreter, KoinlyConfig
from txtool.harmony import DexPriceManager
from txtool.transactions import HarmonyEVMTransaction


def get_csv(events: Sequence[HarmonyEVMTransaction], config: KoinlyConfig) -> str:
    # get fiat prices
    DexPriceManager.initialize_static_price_manager(events)

    # remove out of range
    events = [
        x for x in events if config.dt_lb.timestamp() <= x.timestamp <= config.dt_ub.timestamp()
    ]

    # remove costs
    if config.omit_cost:
        events = [x for x in events if not x.is_cost]

    # build CSV
    return (
            KoinlyInterpreter.get_csv_row_header() +
            "".join(tx.to_csv_row(
                config
            ) for tx in events)
    )
