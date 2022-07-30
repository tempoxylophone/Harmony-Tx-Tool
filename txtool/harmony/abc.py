from abc import ABC
from typing import Any


class Token(ABC):
    def __init__(
        self,
        address: Any,
    ):
        self.address = address
        self.name = ""
        self.symbol = ""
        self.decimals = 0
        self.is_lp_token = False

    def __eq__(self, other) -> bool:  # pragma: no cover
        return isinstance(other, Token) and self.address == other.address

    def __hash__(self) -> int:  # pragma: no cover
        return hash("abstract token" + str(self.address.__hash__()))
