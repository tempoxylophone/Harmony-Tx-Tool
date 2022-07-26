from types import ModuleType
import sys
from . import bech32


def patch_harmony_library() -> ModuleType:
    """
    There is a bug in the official release of the Harmony ONE library.

    github: https://github.com/harmony-one/pyhmy
    pypi: https://pypi.org/project/pyhmy/

    The bug is here, in this folder: https://github.com/harmony-one/pyhmy/tree/master/pyhmy/bech32
    Issue is that there is no __init__.py file, so Python does not see this directory as loadable
    code and this folder is even omitted from the official pypy distribution.

    Verify for yourself:
    https://files.pythonhosted.org/packages/4a/42/bb093003a7ed0f16f77c1e2ee169f24fe9ea0197fec68fab2e190d25718e/pyhmy-20.5.21.tar.gz

    There is an unmerged PR to fix this: https://github.com/harmony-one/pyhmy/pull/32/commits

    For now, to fix, we need to add the correct bech32 file from the repo as intended. That file is here:
    https://github.com/harmony-one/pyhmy/blob/master/pyhmy/bech32/bech32.py

    That file is unaltered since the latest PR that fixed a bug in bech32 default implementation:
    https://github.com/harmony-one/pyhmy/commit/73fb44f1e244de1bd7e801f96f2bf0daa4e41499

    Then we set a reference to this code where the package codebase tries to import it.
    """

    # must do this first otherwise pyhmy is loaded and will throw ModuleNotFoundError
    sys.modules["pyhmy.bech32.bech32"] = bech32
    import pyhmy

    # correct location is actually here
    pyhmy.bech32 = bech32

    return pyhmy  # noqa
