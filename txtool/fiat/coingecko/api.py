from typing import Dict, List, Tuple, NewType
from collections import defaultdict
from functools import lru_cache

import requests

SECONDS_IN_DAY = 86_400
T_COINGECKO_DATAPOINT = Tuple[int, float]
CoingeckoPriceTimeseries = NewType(
    "CoingeckoPriceTimeseries", List[T_COINGECKO_DATAPOINT]
)


@lru_cache(maxsize=1)
def get_coingecko_search_directory() -> Dict:
    headers = {
        "authority": "api.coingecko.com",
        "pragma": "no-cache",
        "cache-control": "no-cache",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "dnt": "1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.42.81 Safari/512.31",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "sec-fetch-site": "none",
        "sec-fetch-mode": "navigate",
        "sec-fetch-user": "?1",
        "sec-fetch-dest": "document",
        "accept-language": "en-US,en;q=0.9",
    }

    params = {
        "locale": "en",
    }

    response: Dict = requests.get(
        "https://api.coingecko.com/api/v3/search", params=params, headers=headers
    ).json()

    return response


def get_coingecko_coin_directory() -> Dict:
    directory = get_coingecko_search_directory()
    formatted_directory = defaultdict(list)

    for d in directory["coins"]:
        formatted_directory[d["symbol"]].append(
            {**d, "internal_id": d["thumb"].split("/images/")[-1].split("/")[0]}
        )

    return formatted_directory


@lru_cache(maxsize=256)
def get_coin_info_by_symbol(coin_symbol: str) -> Dict:
    possible_matches = get_coingecko_coin_directory().get(coin_symbol)
    return next(iter(possible_matches or []), {})


def get_coingecko_chart_data(
    coingecko_coin_object: Dict, unix_timestamp_lb: int, unix_timestamp_ub: int
) -> CoingeckoPriceTimeseries:
    if not coingecko_coin_object:
        # bad coin info given
        return CoingeckoPriceTimeseries([])

    coin_internal_id = coingecko_coin_object["internal_id"]
    coin_id = coingecko_coin_object["id"]

    headers = {
        "authority": "www.coingecko.com",
        "pragma": "no-cache",
        "cache-control": "no-cache",
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
        "dnt": "1",
        "sec-ch-ua-mobile": "?0",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.42.81 Safari/512.31",
        "sec-ch-ua-platform": '"macOS"',
        "accept": "*/*",
        "sec-fetch-site": "same-origin",
        "sec-fetch-mode": "cors",
        "sec-fetch-dest": "empty",
        "referer": f"https://www.coingecko.com/en/coins/{coin_id}",
        "accept-language": "en-US,en;q=0.9",
    }

    lb, ub = adjust_bounds(unix_timestamp_lb, unix_timestamp_ub)
    params = {
        "from": str(lb),
        "to": str(ub),
    }

    response = requests.get(
        f"https://www.coingecko.com/price_charts/{coin_internal_id}/usd/custom.json",
        params=params,
        headers=headers,
    )

    chart_data: Dict[str, List[List]] = response.json()

    return CoingeckoPriceTimeseries(
        [(int(x[0]), float(x[1])) for x in chart_data["stats"]]
    )


def adjust_bounds(lb: int, ub: int) -> Tuple[int, int]:
    if lb == ub:
        # widen by 1 day
        return lb - SECONDS_IN_DAY // 2, ub + SECONDS_IN_DAY // 2

    if ub - lb < SECONDS_IN_DAY:
        # snap to 1 day
        return lb - (SECONDS_IN_DAY - (ub - lb)), ub

    # doesn't need to be changed
    return lb, ub


def get_coingecko_chart_data_by_symbol(
    coin_symbol: str, ts_lb: int, ts_ub: int
) -> CoingeckoPriceTimeseries:
    return get_coingecko_chart_data(get_coin_info_by_symbol(coin_symbol), ts_lb, ts_ub)
