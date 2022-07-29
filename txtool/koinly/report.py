from typing import Optional, Sequence
from datetime import timezone, datetime

from txtool.transactions import HarmonyEVMTransaction
from txtool.harmony import HarmonyToken
from .ruleset import get_label_for_tx_and_description, is_cost


class KoinlyReportCreator:
    _KOINLY_DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
    _KOINLY_ROW_HEADER = [
        "Date",
        "Sent Amount",
        "Sent Currency",
        "Received Amount",
        "Received Currency",
        "Fee Amount",
        "Fee Currency",
        "Net Worth Amount",
        "Net Worth Currency",
        "Label",
        "Description",
        "TxHash",
        "Method",
        "To",
        "From",
        "Explorer URL",
        "\n",
    ]
    _KOINLY_TRACKED_CURRENCY_SYMBOLS = {
        "ONE",
        "ETH",
        "BTC",
        "USDT",
        "USDC",
        "DAI",
        "MATIC",
        "BNB",
        "SOL",
        "DOT",
        "AVAX",
        "LINK",
        "CRV",
    }
    HARMONY_LAUNCH_DATE: datetime = datetime.strptime("2019-05-01", "%Y-%m-%d")

    def __init__(  # pylint: disable=R0913
        self,
        address_format: str,
        omit_tracked_fiat_prices: bool,
        omit_cost: bool,
        date_lb_str: Optional[str] = "",
        date_ub_str: Optional[str] = "",
    ):
        self.address_format = address_format
        self.omit_tracked_fiat_prices = omit_tracked_fiat_prices
        self.omit_cost = omit_cost
        self.dt_lb = (
            self._parse_date_arg(date_lb_str)
            if date_lb_str
            else self.HARMONY_LAUNCH_DATE
        )
        self.dt_ub = (
            self._parse_date_arg(date_ub_str) if date_ub_str else datetime.utcnow()
        )

    def get_csv_from_transactions(self, events: Sequence[HarmonyEVMTransaction]) -> str:
        # remove out of range
        events = [
            x
            for x in events
            if self.dt_lb.timestamp() <= x.timestamp <= self.dt_ub.timestamp()
        ]

        # remove costs
        if self.omit_cost:
            events = [x for x in events if not is_cost(x)]

        return self.get_csv_row_header() + "".join(self.to_csv_row(tx) for tx in events)

    @staticmethod
    def _parse_date_arg(date_str: str) -> datetime:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)

    @staticmethod
    def timestamp_to_utc_datetime(timestamp: int) -> datetime:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def format_utc_ts_as_str(self, timestamp: int) -> str:
        return self.timestamp_to_utc_datetime(timestamp).strftime(
            self._KOINLY_DATE_FORMAT
        )

    def get_csv_row_header(self) -> str:
        return ",".join(self._KOINLY_ROW_HEADER)

    def currency_is_tracked(self, coin_symbol: str) -> bool:
        return coin_symbol.upper() in self._KOINLY_TRACKED_CURRENCY_SYMBOLS

    def to_csv_row(self, tx: HarmonyEVMTransaction) -> str:
        if self.omit_tracked_fiat_prices and self.currency_is_tracked(
            tx.coinType.universal_symbol
        ):
            fiat_value = ""
        else:
            fiat_value = str(tx.get_fiat_value())

        label, desc = get_label_for_tx_and_description(tx)

        return ",".join(
            (
                # time of transaction
                self.format_utc_ts_as_str(tx.timestamp),
                # token sent in this tx (outgoing)
                str(tx.sentAmount or ""),
                tx.sentCurrencySymbol,
                # token received in this tx (incoming)
                str(tx.gotAmount or ""),
                tx.gotCurrencySymbol,
                # gas
                str(tx.tx_fee_in_native_token),
                HarmonyToken.NATIVE_TOKEN_SYMBOL,
                # fiat conversion
                fiat_value,
                tx.fiatType,
                # human readable stuff
                label,
                desc,
                # transaction hash
                tx.txHash,
                tx.get_tx_function_signature(),
                # transfer information
                tx.to_addr.get_address_str(self.address_format),
                tx.from_addr.get_address_str(self.address_format),
                tx.explorer_url,
                "\n",
            )
        )
