import os
import argparse

from txtool.main import get_harmony_tx_from_wallet_as_csv
from txtool.koinly import KoinlyReportCreator
from txtool.harmony import HarmonyAddress

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "wallets", help="Comma separated Ethereum-style address of Harmony ONE wallets"
    )
    parser.add_argument(
        "-s", "--start", help="The starting date for the report (inclusive)"
    )
    parser.add_argument(
        "-e", "--end", help="The ending date for the report (inclusive)"
    )

    args = parser.parse_args()

    # go through each wallet and export transactions
    wallet_addresses = [x.strip() for x in args.wallets.split(",")]

    report = KoinlyReportCreator(
        address_format=HarmonyAddress.FORMAT_ONE,
        omit_tracked_fiat_prices=True,
        omit_cost=True,
        date_lb_str=args.start,
        date_ub_str=args.end,
    )

    for wallet_address in wallet_addresses:
        # run program
        csv_contents, file_name = get_harmony_tx_from_wallet_as_csv(
            wallet_address,
            report,
        )

        # write result to desktop
        user_dir = os.path.expanduser("~")
        path = user_dir + "/Desktop/" + file_name
        with open(path, "w") as f:
            f.write(csv_contents)
