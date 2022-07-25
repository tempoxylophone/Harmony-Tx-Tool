from datetime import timezone, datetime

KOINLY_ROW_HEADER = [
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
    '\n',
]
KOINLY_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %Z'


class KoinlyInterpreter:

    @staticmethod
    def parse_utc_ts(timestamp: int) -> str:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).strftime(
            KOINLY_DATE_FORMAT
        )
