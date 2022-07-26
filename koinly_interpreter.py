from typing import Dict
from json import loads
from datetime import timezone, datetime
import requests
import re


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
    KOINLY_USE_ONE_ADDRESS_FORMAT = True
    EXPLORER_URL = "https://explorer.harmony.one/"

    # get script tag's source attribute that ends with .js extension and has the path /bundles/ in it
    EXPLORER_BUNDLE_LINK_REGEX = r"src='((?:https):\/\/(?:.+?\/)?(?:bundles\/[\w_.\/-]+)\.js)'"

    # get the dumped JSON in the bundle that is a k, v pair of ethereum address to some word (i.e. token name)
    EXPLORER_BUNDLE_TOKEN_JSON_REGEX = r"=JSON\.parse\('({(?:\"0x[a-fA-F0-9]{40}\":\"\w+\").+\"})'\)"

    # compile these only once, static variable
    _r_find_explorer_link = re.compile(EXPLORER_BUNDLE_LINK_REGEX)
    _r_find_token_dict = re.compile(EXPLORER_BUNDLE_LINK_REGEX)

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

    @classmethod
    def get_harmony_tokens_directory(cls) -> Dict[str, str]:
        return cls._get_token_json_from_bundle(cls._get_explorer_bundle_as_string())

    @classmethod
    def _get_explorer_bundle_url(cls) -> str:
        page_html = requests.get(cls.EXPLORER_URL).text
        return cls._r_find_explorer_link.search(page_html).group(1)

    @classmethod
    def _get_explorer_bundle_as_string(cls) -> str:
        return requests.get(cls._get_explorer_bundle_url()).text

    @classmethod
    def _get_token_json_from_bundle(cls, bundle_as_string: str) -> Dict[str, str]:
        # BUG: causes catastrophic backtracking in regex
        json_blob = cls._r_find_token_dict.search(bundle_as_string).group(1)
        return loads(json_blob)
