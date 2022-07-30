from datetime import timezone
from txtool.koinly import KoinlyReportCreator
from txtool.transactions import WalletActivity


def test_koinly_tracked_currency():
    assert KoinlyReportCreator.currency_is_tracked("ONE")
    assert KoinlyReportCreator.currency_is_tracked("USDC")
    assert KoinlyReportCreator.currency_is_tracked("ETH")
    assert not KoinlyReportCreator.currency_is_tracked("JENN")


def test_timestamp_conversions():
    assert "2022-07-30 14:05:28 UTC" == KoinlyReportCreator.format_utc_ts_as_str(
        1659189928
    )


def test_create_koinly_report_creator():
    lb_str = "2019-05-01"
    ub_str = "2022-01-01"
    report = KoinlyReportCreator(
        date_lb_str=lb_str,
        date_ub_str=ub_str,
    )
    assert report.dt_lb.strftime("%Y-%m-%d") == lb_str
    assert report.dt_ub.strftime("%Y-%m-%d") == ub_str
    assert report.dt_lb.tzinfo == timezone.utc
    assert report.dt_ub.tzinfo == timezone.utc


def test_omit_costs():
    # random TX from explorers with smart contract interaction
    tx_hash = "0x8afcd2fef1bad1f048e90902834486771c589b08c9040b5ab6789ad98775bb13"
    wallet_address = "0x974190a07ff72043bdeaa1f6bfe90bdd33172e51"
    txs = WalletActivity.extract_all_wallet_activity_from_transaction(
        wallet_address,
        tx_hash,
    )

    assert len(txs) == 2

    no_cost_config = KoinlyReportCreator(omit_cost=True)
    no_cost_report = no_cost_config.get_csv_from_transactions(txs)

    cost_config = KoinlyReportCreator(omit_cost=False)
    cost_report = cost_config.get_csv_from_transactions(txs)

    # should include extra row
    assert len(cost_report) > len(no_cost_report)
