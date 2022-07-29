from typing import Tuple
from datetime import datetime
from txtool.koinly import KoinlyConfig
from txtool.harmony import HarmonyAPI
from txtool.generate import get_csv
from txtool.events import get_events


def get_harmony_tx_from_wallet_as_csv(
        wallet_address_eth_str: str,
        report_config: KoinlyConfig,
) -> Tuple[str, str]:
    # --- START ---
    print("Fetching {0} transactions from address {1}...".format(
        HarmonyAPI.get_num_tx_for_wallet(wallet_address_eth_str),
        wallet_address_eth_str
    ))

    # --- GET + PARSE DATA FROM BLOCKCHAIN ---
    tx_events = get_events(
        HarmonyAPI.get_harmony_tx_list(wallet_address_eth_str),
        wallet_address_eth_str
    )

    # --- WRITE TO FILE ---
    result: str = get_csv(
        tx_events,
        report_config
    )
    _finished_at = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    _file_name = wallet_address_eth_str + "_" + _finished_at + ".csv"
    return result, _file_name
