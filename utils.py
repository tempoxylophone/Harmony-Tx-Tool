from typing import List, Callable, Tuple, Union
import os
from requests.exceptions import HTTPError, ConnectionError
from tenacity import (
    retry,
    retry_any as RetryChain,  # noqa
    stop_after_attempt,
    retry_if_exception_type as r,
    wait_exponential,
    wait_random,
)

COMMON_API_EXCEPTIONS = (
    HTTPError,
    ConnectionError,
)


def retry_on_exceptions(
        exceptions: Union[List[Exception], Tuple[Exception]],
        max_tries: int = 5,
        jitter_range_sec: int = 2,
        max_wait_sec: int = 120
) -> Callable:
    return retry(
        retry=_build_exceptions(exceptions),
        reraise=True,
        wait=(
                wait_exponential(multiplier=1, min=5, max=max_wait_sec) +
                wait_random(0, jitter_range_sec)
        ),
        stop=stop_after_attempt(max_tries)
    )


def _build_exceptions(exceptions, i=0) -> RetryChain:
    # hahah
    return r(exceptions[i]) | (
            i + 1 == len(exceptions) - 1 and r(exceptions[i + 1]) or _build_exceptions(exceptions, i + 1)
    )


def api_retry() -> Callable:
    return retry_on_exceptions(COMMON_API_EXCEPTIONS)  # noqa (type inheritance fails here)


def get_local_abi(abi_json_filename: str) -> str:
    location = os.path.abspath(__file__)
    path = '{0}/abi/{1}.json'.format(
        '/'.join(location.split('/')[0:-1]),
        abi_json_filename
    )

    with open(path, 'r') as f:
        abi = f.read()

    return abi
