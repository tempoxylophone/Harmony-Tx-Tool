from txtool.main import get_harmony_tx_from_wallet_as_csv
from txtool.koinly import KoinlyReportCreator

from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_create_koinly_report_with_no_transactions():
    # address from pyhmy test cases
    wallet_address = "0xeBCD16e8c1D8f493bA04E99a56474122D81A9c58"

    report = KoinlyReportCreator()

    csv_contents, _ = get_harmony_tx_from_wallet_as_csv(
        wallet_address,
        report,
    )

    # should be empty
    assert report.get_csv_row_header() == csv_contents
