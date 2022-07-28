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
    def format_utc_ts_as_str(timestamp: int) -> str:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).strftime(
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


class KoinlyConfig:
    ROW_HEADER = KoinlyInterpreter._KOINLY_ROW_HEADER  # noqa

    def __init__(self, address_format: str, omit_tracked_fiat_prices: bool):
        self.address_format = address_format
        self.omit_tracked_fiat_prices = omit_tracked_fiat_prices
