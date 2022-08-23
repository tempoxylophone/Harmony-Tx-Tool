from __future__ import annotations
from functools import lru_cache
import re

import requests

from txtool.utils import api_retry

_LOOKUP_BASE_URL = "https://www.4byte.directory/signatures/?bytes4_signature={0}"
_CAPTURE_METHOD_NAME_REGEX = r"<td class=\"text_signature\">(.*)<\/td>"
_HEADERS = {
    "Connection": "keep-alive",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_14_6) "
    "AppleWebKit/532.36 (KHTML, like Gecko) Chrome/99.0.414.84 Safari/517.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
    "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Referer": "https://www.4byte.directory/",
    "Accept-Language": "en-US,en;q=0.9",
}


@lru_cache(maxsize=256)
def get_function_name_by_signature(function_signature: str) -> str:
    """
    Since Harmony is EVM compatible, we can use 4byte to approximate
    the method signature
    """
    if not isinstance(function_signature, str) or len(function_signature) != 10:
        # invalid signature
        return ""

    return _do_request(function_signature)


@api_retry()
def _do_request(function_signature: str) -> str:
    # get from the internet
    r = requests.get(
        _get_url(function_signature),
        headers=_HEADERS,
    )

    # find it in html
    k = re.search(_CAPTURE_METHOD_NAME_REGEX, r.text)

    # if you can't find it, signature is invalid, return blank
    return str(k.group(1)) if k else ""


def _get_url(function_signature: str) -> str:
    return _LOOKUP_BASE_URL.format(function_signature)
