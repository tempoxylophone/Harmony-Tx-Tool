from typing import Tuple
import os
from harmony import HarmonyAPI
import taxmap
import datetime
import argparse
from generate import get_csv

TODAY_DATE_STR = datetime.date.today().strftime("%Y-%m-%d")


def main() -> Tuple[str, str, str]:
    # cmd arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("wallet", help="The evm compatible wallet address to generate for")
    args = parser.parse_args()

    wallet_eth_address_str: str = args.wallet

    # list of transactions if loaded from file if available, otherwise fetched
    num_transactions: int = HarmonyAPI.get_num_tx_for_wallet(wallet_eth_address_str)

    print("Fetching {0} transactions from address {1}...".format(num_transactions, args.wallet))

    # With transaction list, we now generate the events and tax map
    reportData = taxmap.buildTaxMap(
        HarmonyAPI.get_harmony_tx_list(args.wallet),
        wallet_eth_address_str,
        HarmonyAPI.HARMONY_LAUNCH_DATE,
        datetime.datetime.strptime(TODAY_DATE_STR, '%Y-%m-%d').date(),
        'fifo',
        {
            'purchaseAddresses': []
        }
    )

    result: str = get_csv(reportData)
    _finished_at = datetime.datetime.now().strftime("%Y-%m-%d_%H:%m:%s")
    return wallet_eth_address_str, _finished_at, result


if __name__ == "__main__":
    addr, finished_at, tx_csv_str = main()

    # write to desktop
    user_dir = os.path.expanduser("~")
    with open(user_dir + "/Desktop/{0}_{1}".format(addr, finished_at) + ".csv", "w") as f:
        f.write(tx_csv_str)
