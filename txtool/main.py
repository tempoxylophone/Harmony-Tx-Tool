from typing import Tuple
import os
import datetime
import argparse

from txtool.harmony import HarmonyAPI
from txtool.generate import get_csv
from txtool.events import get_events

TODAY_DATE_STR = datetime.date.today().strftime("%Y-%m-%d")


def get_harmony_tx_from_wallet_as_csv(wallet_address_eth_str: str) -> Tuple[str, str]:
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
    result: str = get_csv(tx_events)
    _finished_at = datetime.datetime.now().strftime("%Y-%m-%d_%H:%m:%s")
    _file_name = wallet_address_eth_str + "_" + _finished_at + ".csv"
    return result, _file_name


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wallet", help="Ethereum-style address of Harmony ONE wallet")
    args = parser.parse_args()

    csv_contents, file_name = get_harmony_tx_from_wallet_as_csv(args.wallet)

    # write to desktop
    user_dir = os.path.expanduser("~")
    path = user_dir + "/Desktop/" + file_name
    with open(path, "w") as f:
        f.write(csv_contents)
