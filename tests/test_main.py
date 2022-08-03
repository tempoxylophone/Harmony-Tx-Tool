import logging
from txtool.koinly import KoinlyReportCreator
from txtool.harmony import HarmonyAddress
from txtool.main import get_harmony_tx_from_wallet_as_csv
from txtool.utils import MAIN_LOGGER
from txtool.harmony import DexPriceManager

from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_export_full_tx_log_for_koinly():
    DexPriceManager.clear_state()

    # turn logging on
    MAIN_LOGGER.setLevel(logging.INFO)

    report_creator = KoinlyReportCreator(
        address_format=HarmonyAddress.FORMAT_ONE,
        omit_tracked_fiat_prices=True,
        omit_cost=False,
        # there are lots of tx in this wallet
        date_lb_str="2022-07-28",
        date_ub_str="2022-07-29",
        tx_limit=20,
    )

    # random address from explorer
    wallet_eth_address_str = "0xcc508e2c48e41d1ad674df40014a522d597fc0b5"

    csv_contents, _ = get_harmony_tx_from_wallet_as_csv(
        wallet_eth_address_str, report_creator
    )

    # very weak acceptance criteria but this is just to test end to end program
    assert csv_contents

    # turn logging off for other tests
    MAIN_LOGGER.setLevel(logging.ERROR)

    DexPriceManager.clear_state()
