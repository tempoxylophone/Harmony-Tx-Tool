from typing import Tuple
import transactions
import taxmap
import datetime
import argparse
import logging
import logging.handlers
from generate import get_csv

HARMONY_LAUNCH_DATE_STR = "2019-05-01"
TODAY_DATE_STR = datetime.date.today().strftime("%Y-%m-%d")
TX_PAGE_SIZE = 1_000


def main() -> Tuple[str, str, str]:
    logging.basicConfig()

    # cmd arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("wallet", help="The evm compatible wallet address to generate for")
    parser.add_argument("--costbasis", choices=['fifo', 'lifo', 'hifo', 'acb'],
                        help="Method for mapping cost basis to gains")
    args = parser.parse_args()

    # default to FIFO
    costBasis = args.costbasis or 'fifo'

    # defaults
    moreOptions = {
        'purchaseAddresses': []
    }

    report_wallet_address_eth: str = args.wallet

    # list of transactions if loaded from file if available, otherwise fetched
    num_transactions: int = transactions.get_num_tx_for_wallet(report_wallet_address_eth)

    print("Fetching {0} transactions from address {1}...".format(num_transactions, args.wallet))

    # With transaction list, we now generate the events and tax map
    reportData = taxmap.buildTaxMap(
        transactions.get_harmony_tx_list(args.wallet, TX_PAGE_SIZE),
        report_wallet_address_eth,
        datetime.datetime.strptime(HARMONY_LAUNCH_DATE_STR, '%Y-%m-%d').date(),
        datetime.datetime.strptime(TODAY_DATE_STR, '%Y-%m-%d').date(),
        costBasis,
        moreOptions
    )

    result: str = get_csv(reportData)
    _finished_at = datetime.datetime.now().strftime("%Y-%m-%d_%H:%m:%s")
    return report_wallet_address_eth, _finished_at, result


if __name__ == "__main__":
    addr, finished_at, tx_csv_str = main()
    with open("./{0}_{1}".format(addr, finished_at) + ".csv", "w") as f:
        f.write(tx_csv_str)
