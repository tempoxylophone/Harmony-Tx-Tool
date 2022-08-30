from typing import Tuple, Sequence, List
from datetime import datetime
from eth_typing import HexStr

from .harmony import HarmonyAPI, HarmonyAddress, WalletActivity
from .activity.interpreter import get_interpreted_transactions
from .koinly import KoinlyReportCreator

from .utils import MAIN_LOGGER, make_red


def get_harmony_tx_from_wallet_as_csv(
    wallet_address_eth_str: str,
    report: KoinlyReportCreator,
) -> Tuple[str, str]:
    # --- START ---
    MAIN_LOGGER.info(
        "Fetching transactions from address %s...",
        wallet_address_eth_str,
    )

    tx_hashes = HarmonyAPI.get_harmony_tx_list(
        wallet_address_eth_str, report.dt_lb_ts, report.dt_ub_ts
    )[: report.tx_limit]

    # --- GET + PARSE DATA FROM BLOCKCHAIN ---
    account = HarmonyAddress.get_harmony_address_by_string(wallet_address_eth_str)
    tx_events = get_events(account, tx_hashes)

    MAIN_LOGGER.info("Done interpreting transactions.")

    # --- WRITE TO FILE ---
    # build CSV
    MAIN_LOGGER.info("Writing results to file...")
    result_csv = report.get_csv_from_transactions(tx_events)

    # return with filename
    _finished_at = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    _file_name = wallet_address_eth_str + "_" + _finished_at + ".csv"
    return result_csv, _file_name


def get_events(
    account: HarmonyAddress, tx_hashes_strings: List[HexStr]
) -> Sequence[WalletActivity]:
    events: List[WalletActivity] = []

    total_tx = len(tx_hashes_strings)
    for i, tx_hash_string in enumerate(tx_hashes_strings):
        MAIN_LOGGER.info(
            "Working on transaction: %s (%s/%s). Extracting all sub-transactions.",
            tx_hash_string,
            i + 1,
            total_tx,
        )

        receipt = HarmonyAPI.get_tx_receipt(tx_hash_string)

        if receipt["status"] != 1:  # pragma: no cover
            # in progress?
            continue

        # token transfers and fees associated with them
        try:
            results = get_interpreted_transactions(
                account,
                tx_hash_string,
            )
            events += results
        except Exception as e:  # pylint: disable=W0703; # pragma: no cover
            MAIN_LOGGER.warning(
                make_red(
                    "Transaction %s threw error: %s ..." % (tx_hash_string, str(e))
                )
            )

    return events
