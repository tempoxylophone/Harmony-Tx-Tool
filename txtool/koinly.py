from typing import Optional
from datetime import timezone, datetime
from enum import Enum


class KoinlyLabel(str, Enum):
    COST = 'cost'
    NULL = ''


class KoinlyInterpreter:
    _KOINLY_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %Z'
    _KOINLY_ROW_HEADER = [
        'Date',
        'Sent Amount',
        'Sent Currency',
        'Received Amount',
        'Received Currency',
        'Fee Amount',
        'Fee Currency',
        'Net Worth Amount',
        'Net Worth Currency',
        'Label',
        'Description',
        'TxHash',
        'Method',
        'To',
        'From',
        'Explorer URL',
        '\n',
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

    @staticmethod
    def timestamp_to_utc_datetime(timestamp: int) -> datetime:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        )

    @staticmethod
    def format_utc_ts_as_str(timestamp: int) -> str:
        return KoinlyInterpreter.timestamp_to_utc_datetime(timestamp).strftime(
            KoinlyInterpreter._KOINLY_DATE_FORMAT
        )

    @staticmethod
    def get_csv_row_header() -> str:
        return ",".join(KoinlyInterpreter._KOINLY_ROW_HEADER)

    @staticmethod
    def is_tracked(coin_symbol: str) -> bool:
        return coin_symbol.upper() in KoinlyInterpreter._KOINLY_TRACKED_CURRENCY_SYMBOLS

    @staticmethod
    def getRecordLabel(_, event_type: str, event: str) -> str:
        if event_type == 'gardens':
            if event == 'staking-reward':
                return 'reward'
            else:
                return 'ignored'
        elif event_type == 'tavern':
            if event == 'sale':
                return 'realized gain'
            elif event == 'hire':
                return 'income'
            else:
                return 'cost'

        return ""


class KoinlyConfig:
    HARMONY_LAUNCH_DATE: datetime = datetime.strptime("2019-05-01", '%Y-%m-%d')
    ROW_HEADER = KoinlyInterpreter._KOINLY_ROW_HEADER  # noqa

    def __init__(
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
        self.dt_lb = date_lb_str and self._parse_date_arg(date_lb_str) or self.HARMONY_LAUNCH_DATE
        self.dt_ub = date_ub_str and self._parse_date_arg(date_ub_str) or datetime.utcnow()

    @staticmethod
    def _parse_date_arg(date_str: str) -> datetime:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
