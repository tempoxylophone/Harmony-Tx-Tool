from typing import Optional, Sequence, List
from datetime import timezone, datetime

from txtool.harmony import (
    HarmonyAddress,
    HarmonyAPI,
    WalletActivity,
)
from txtool.fiat.get_prices import get_token_prices_for_transactions

from txtool.csv.transaction_wrapper import TransactionCSVWrapper


class TransactionReportCreator:
    HARMONY_LAUNCH_DATE: datetime = datetime.utcfromtimestamp(
        HarmonyAPI.get_timestamp(1)
    )
    DATE_FORMAT = ""
    HEADER = [""]

    def __init__(  # pylint: disable=R0913
        self,
        address_format: str = HarmonyAddress.FORMAT_ONE,
        omit_tracked_fiat_prices: bool = True,
        date_lb_str: str = "",
        date_ub_str: str = "",
        tx_limit: Optional[int] = None,
    ):
        self.address_format: str = address_format or HarmonyAddress.FORMAT_ONE
        self.omit_tracked_fiat_prices = omit_tracked_fiat_prices

        # date bounds
        self.dt_lb = (
            self._parse_date_arg(date_lb_str)
            if date_lb_str
            else self.HARMONY_LAUNCH_DATE
        )
        self.dt_ub = (
            self._parse_date_arg(date_ub_str) if date_ub_str else datetime.utcnow()
        )

        # round to nearest second
        self.dt_lb_ts = int(self.dt_lb.timestamp())
        self.dt_ub_ts = int(self.dt_ub.timestamp())

        # mostly for testing, cap the number of tx you can generate in a report
        self.tx_limit = tx_limit

    def get_wrapped_transactions(
        self, events: Sequence[WalletActivity]
    ) -> List[TransactionCSVWrapper]:
        # get prices to use later
        price_lookup = get_token_prices_for_transactions(events)

        # remove out of range
        parsed_events = [
            TransactionCSVWrapper(
                x,
                price_lookup,
                use_universal_symbol=True,
                use_one_address_style=True,
                date_format=self.DATE_FORMAT,
            )
            for x in events
            if self.timestamp_is_in_bounds(x.timestamp) and not x.did_fail
        ]

        return parsed_events

    def build_csv_from_events(self, events: List[TransactionCSVWrapper]) -> str:
        # build the csv
        return self.get_csv_row_header() + "".join(
            self.to_csv_row_str(tx) for tx in events
        )

    def get_csv_from_transactions(self, events: Sequence[WalletActivity]) -> str:
        return self.build_csv_from_events(self.get_wrapped_transactions(events))

    def timestamp_is_in_bounds(self, ts: int) -> bool:
        return self.dt_lb_ts <= ts <= self.dt_ub_ts

    @staticmethod
    def _parse_date_arg(date_str: str) -> datetime:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)

    def get_csv_row_header(self) -> str:
        return ",".join(self.HEADER)

    def to_csv_row_str(self, tx: TransactionCSVWrapper) -> str:  # pragma: no cover
        raise NotImplementedError
