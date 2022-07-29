from typing import Tuple, Optional
from datetime import datetime, timezone

from txtool.harmony import HarmonyAPI
from txtool.generate import get_csv
from txtool.events import get_events


def get_harmony_tx_from_wallet_as_csv(
        wallet_address_eth_str: str,
        dt_arg_lb: Optional[str] = "",
        dt_arg_ub: Optional[str] = "",
) -> Tuple[str, str]:
    dt_lb = dt_arg_lb and _parse_date_arg(dt_arg_lb) or HarmonyAPI.HARMONY_LAUNCH_DATE
    dt_ub = dt_arg_ub and _parse_date_arg(dt_arg_ub) or datetime.utcnow()

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

    # remove out of range transactions
    tx_events = [x for x in tx_events if dt_lb.timestamp() <= x.timestamp <= dt_ub.timestamp()]

    # --- WRITE TO FILE ---
    result: str = get_csv(tx_events)
    _finished_at = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    _file_name = wallet_address_eth_str + "_" + _finished_at + ".csv"
    return result, _file_name


def _parse_date_arg(date_str: str) -> datetime:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)
