from typing import Generator
import gc
import functools
import pytest  # noqa

from txtool.harmony import (
    HarmonyAddress,
    HarmonyToken,
    HarmonyNFT,
    HarmonyNFTCollection,
)


@pytest.fixture(autouse=True)
def run_before_and_after_tests() -> Generator:
    # this must be cleared on each test, otherwise requests are inconsistent
    # and vcrpy records inconsistent behavior
    HarmonyNFTCollection.clear_directory()
    HarmonyAddress.clear_directory()
    HarmonyToken.clear_directory()
    HarmonyNFT.clear_directory()

    # source: https://stackoverflow.com/a/50699209
    # clear any cache state for lru_cache decorators in our entire program
    gc.collect()
    wrappers = [
        a
        for a in gc.get_objects()
        if isinstance(a, functools._lru_cache_wrapper)  # noqa
    ]

    for wrapper in wrappers:
        wrapper.cache_clear()

    # run test here
    yield
