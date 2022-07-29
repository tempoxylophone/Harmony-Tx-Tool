import os
import argparse

from txtool.main import get_harmony_tx_from_wallet_as_csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("wallet", help="Ethereum-style address of Harmony ONE wallet")
    parser.add_argument("start_date", help="The starting date for the report (inclusive)")
    parser.add_argument("end_date", help="The ending date for the report (inclusive)")

    args = parser.parse_args()

    # run program
    csv_contents, file_name = get_harmony_tx_from_wallet_as_csv(
        args.wallet,
        args.start_date,
        args.end_date,
    )

    # write result to desktop
    user_dir = os.path.expanduser("~")
    path = user_dir + "/Desktop/" + file_name
    with open(path, "w") as f:
        f.write(csv_contents)
