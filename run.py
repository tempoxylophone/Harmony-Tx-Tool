import os
import logging
import argparse

from txtool.main import get_harmony_tx_from_wallet_as_csv
from txtool.koinly import KoinlyReportCreator
from txtool.harmony import HarmonyAddress
from txtool.utils import MAIN_LOGGER

LOG_LEVELS = {"error": logging.ERROR, "info": logging.INFO, "debug": logging.DEBUG}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wallet", help="Ethereum-style address of Harmony ONE wallet")
    parser.add_argument(
        "-s", "--start", help="The starting date for the report (inclusive)"
    )
    parser.add_argument(
        "-e", "--end", help="The ending date for the report (inclusive)"
    )
    parser.add_argument(
        "-l", "--log", default=logging.ERROR, help="Log level, default = error"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=LOG_LEVELS[args.log],
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # go through each wallet and export transactions
    wallet_address = args.wallet

    report = KoinlyReportCreator(
        omit_cost=True,
        date_lb_str=args.start,
        date_ub_str=args.end,
    )

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

    MAIN_LOGGER.info("Done. Goodbye!")
