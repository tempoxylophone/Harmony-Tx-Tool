import gc
import functools
import pytest  # noqa

from txtool.fiat import DexPriceManager
from txtool.harmony import HarmonyAddress, HarmonyToken

# file must be called "conftest" in order to be shared by all in this directory
# see: https://docs.pytest.org/en/6.2.x/fixture.html#scope-sharing-fixtures-across-classes-modules-packages-or-session


@pytest.fixture(autouse=True)
def run_before_and_after_tests():
    # this must be cleared on each test, otherwise requests are inconsistent
    # and vcrpy records inconsistent behavior
    HarmonyAddress.clear_directory()
    HarmonyToken.clear_directory()

    # source: https://stackoverflow.com/a/50699209

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
