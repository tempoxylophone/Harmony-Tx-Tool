from __future__ import annotations
from abc import ABC
from typing import Any, Optional, Union
from datetime import datetime
from decimal import Decimal


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

    @property
    def is_native_token(self) -> bool:  # pragma: no cover
        return False

    @classmethod
    def get_native_token(cls) -> Token:  # pragma: no cover
        raise NotImplementedError


class Transaction(ABC):  # pylint: disable=R0902
    def __init__(self, account: Any, tx_hash: Any):
        self.tx_hash = tx_hash
        self.account = account

        self.block = 1
        self.timestamp = -1
        self.block_date = datetime.now().date()

        self.coin_type: Union[Token, None] = None
        self.coin_amount = Decimal(0)
        self.tx_fee_in_native_token = Decimal(0)

        # (placeholder values)
        # token sent in this tx (outgoing)
        self.sent_amount = 0
        self.sent_currency_symbol = ""

        # token received in this tx (incoming)
        self.got_amount = 0
        self.got_currency_symbol = ""

    def get_fiat_value(self, exclude_fee: Optional[bool] = False) -> Decimal:
        t_val = self.coin_amount * self.get_token_price()
        f_val = (
            Decimal(0)
            if exclude_fee
            else self.tx_fee_in_native_token * self.get_fee_price()
        )
        return t_val + f_val

    def get_token_price(self) -> Decimal:  # pragma: no cover
        raise NotImplementedError

    def get_fee_price(self) -> Decimal:  # pragma: no cover
        raise NotImplementedError
