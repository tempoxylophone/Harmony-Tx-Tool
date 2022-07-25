from typing import Tuple
import transactions
import taxmap
import settings
import datetime
import argparse
import logging
import logging.handlers
from generate import get_csv


def main() -> Tuple[str, str, str]:
    logging.basicConfig()

    # cmd arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("wallet", help="The evm compatible wallet address to generate for")
    parser.add_argument("startDate", help="The starting date for the report")
    parser.add_argument("endDate", help="The ending date for the report")
    parser.add_argument("--costbasis", choices=['fifo', 'lifo', 'hifo', 'acb'],
                        help="Method for mapping cost basis to gains")
    args = parser.parse_args()

    # default to FIFO
    costBasis = args.costbasis or 'fifo'

    # defaults
    page_size = settings.TX_PAGE_SIZE
    moreOptions = {
        'purchaseAddresses': []
    }

    report_wallet_address_eth: str = args.wallet

    # list of transactions if loaded from file if available, otherwise fetched
    num_transactions: int = transactions.get_num_tx_for_wallet(report_wallet_address_eth)
    print("Fetching {0} transactions from address {1}...".format(num_transactions, args.wallet))

    # fetch hashes only from harmony blockchain
    tx_hashes = transactions.get_harmony_tx_list(args.wallet, page_size)

    # With transaction list, we now generate the events and tax map
    reportData = taxmap.buildTaxMap(
        tx_hashes,
        report_wallet_address_eth,
        datetime.datetime.strptime(args.startDate, '%Y-%m-%d').date(),
        datetime.datetime.strptime(args.endDate, '%Y-%m-%d').date(),
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
