from datetime import timezone
from txtool.koinly import KoinlyReportCreator
from .utils import get_vcr

vcr = get_vcr(__file__)


def test_koinly_tracked_currency() -> None:
    assert KoinlyReportCreator.currency_is_tracked("ONE")
    assert KoinlyReportCreator.currency_is_tracked("USDC")
    assert KoinlyReportCreator.currency_is_tracked("ETH")
    assert not KoinlyReportCreator.currency_is_tracked("JENN")


def test_timestamp_conversions() -> None:
    assert "2022-07-30 14:05:28 UTC" == KoinlyReportCreator.format_utc_ts_as_str(
        1659189928
    )


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
