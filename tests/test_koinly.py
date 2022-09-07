from datetime import timezone
from txtool.tax.koinly import KoinlyReportCreator


def test_koinly_tracked_currency() -> None:
    assert KoinlyReportCreator.currency_is_tracked("ONE")
    assert KoinlyReportCreator.currency_is_tracked("USDC")
    assert KoinlyReportCreator.currency_is_tracked("ETH")
    assert not KoinlyReportCreator.currency_is_tracked("JENN")


def test_create_koinly_report_creator() -> None:
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
