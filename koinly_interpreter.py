from datetime import timezone, datetime


class KoinlyInterpreter:
    KOINLY_DATE_FORMAT = '%Y-%m-%d %H:%M:%S %Z'
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
        'To',
        'From',
        '\n',
    ]


    @staticmethod
    def parse_utc_ts(timestamp: int) -> str:
        return datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc
        ).strftime(
            KoinlyInterpreter.KOINLY_DATE_FORMAT
        )

    @staticmethod
    def get_csv_row_header() -> str:
        return ",".join(KoinlyInterpreter.KOINLY_ROW_HEADER)
