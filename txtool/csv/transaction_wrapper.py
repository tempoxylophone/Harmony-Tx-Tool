from typing import Literal, Optional
from decimal import Decimal
from datetime import timezone, datetime

from txtool.harmony import WalletActivity, HarmonyToken, HarmonyNFT

from txtool.harmony.constants import NATIVE_TOKEN_SYMBOL

from txtool.fiat.get_prices import T_PRICE_DATA_DICT
from txtool.tax.koinly.ruleset.fixes import KOINLY_UNSUPPORTED_COIN_NAMES


class TransactionCSVWrapper:
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z"

    def __init__(  # pylint: disable=R0913
        self,
        transaction: WalletActivity,
        price_lookup: T_PRICE_DATA_DICT,
        use_universal_symbol: bool = True,
        use_one_address_style: bool = True,
        omit_cost: bool = False,
        date_format: str = DEFAULT_DATE_FORMAT,
    ) -> None:
        self.tx = transaction
        self._price_lookup = price_lookup
        self._use_universal_symbol = use_universal_symbol
        self._omit_cost = omit_cost
        self._date_format = date_format
        self._address_format: Literal["one", "eth"] = (
            "one" if use_one_address_style else "eth"
        )

    @staticmethod
    def _timestamp_to_utc_datetime(timestamp: int) -> datetime:
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def _format_utc_ts_as_str(self, timestamp: int) -> str:
        return TransactionCSVWrapper._timestamp_to_utc_datetime(timestamp).strftime(
            self._date_format
        )

    @property
    def date(self) -> str:
        return self._format_utc_ts_as_str(self.tx.timestamp)

    @property
    def coin_symbol(self) -> str:
        if self._use_universal_symbol:
            return self.tx.coin_type.universal_symbol
        return self.tx.coin_type.symbol

    @property
    def sent_amount(self) -> str:
        return str(self.tx.sent_amount or "")

    @property
    def sent_currency(self) -> str:
        if not self.tx.sent_currency:
            # null coin
            return ""
        if self._use_universal_symbol:
            return self.tx.sent_currency.universal_symbol
        return self.tx.sent_currency.symbol

    @property
    def got_amount(self) -> str:
        return str(self.tx.got_amount or "")

    @property
    def got_currency(self) -> str:
        if not self.tx.got_currency:
            # null coin
            return ""
        if self._use_universal_symbol:
            return self.tx.got_currency.universal_symbol
        return self.tx.got_currency.symbol

    @property
    def fee_amount(self) -> str:
        return "0" if self._omit_cost else str(self.tx.tx_fee_in_native_token)

    @property
    def fee_currency(self) -> str:
        # always is ONE
        return NATIVE_TOKEN_SYMBOL

    @property
    def net_worth_amount(self) -> str:
        if (
            not isinstance(self.tx.coin_type, HarmonyToken)
            or self.tx.coin_type.__class__ != HarmonyToken
        ):
            # got placeholder token, don't look it up
            return ""

        if self.tx.is_trade:
            # use the token received to determine the networth amount of
            # the trade
            if not isinstance(self.tx.got_currency, HarmonyToken) or not isinstance(
                self.tx.sent_currency, HarmonyToken
            ):
                raise RuntimeError(
                    (
                        "Invalid currency types for net worth calculation "
                        "of transaction (trade): %s",
                        self.tx,
                    ),
                )

            coins = [
                (
                    self.tx.got_currency,
                    self.tx.got_amount,
                    self._price_lookup[self.tx].get(self.tx.got_currency),
                ),
                (
                    self.tx.sent_currency,
                    self.tx.sent_amount,
                    self._price_lookup[self.tx].get(self.tx.sent_currency),
                ),
            ]
            coin_choice = next(
                (
                    x
                    for x in coins
                    if (x[0] and x[0].symbol not in KOINLY_UNSUPPORTED_COIN_NAMES)
                    and bool(x[2])
                ),
                None,
            )

            if not coin_choice:
                # neither coin is supported by Koinly
                return ""

            _, coin_amount, usd_price = coin_choice
            return str(self._safe_mul(coin_amount, usd_price) or "")

        # regular send/receive
        token_quantity = (
            self.tx.got_amount if self.tx.is_receiver else self.tx.sent_amount
        )
        coin_type = (
            self.tx.got_currency if self.tx.is_receiver else self.tx.sent_currency
        )

        if not isinstance(coin_type, HarmonyToken):
            raise RuntimeError(
                (
                    "Invalid currency types for net worth calculation of "
                    "transaction (send/receive): %s",
                    self.tx,
                ),
            )

        token_usd_price = self._price_lookup[self.tx][coin_type]
        return str(self._safe_mul(token_quantity, token_usd_price) or "")

    @staticmethod
    def _safe_mul(a: Optional[Decimal], b: Optional[Decimal]) -> Decimal:
        return (a or Decimal(0)) * (b or Decimal(0))

    @property
    def net_worth_currency(self) -> str:
        return "usd"

    @property
    def tx_hash(self) -> str:
        return str(self.tx.tx_hash)

    @property
    def method(self) -> str:
        return self.tx.method_for_csv_export

    @property
    def to_addr(self) -> str:
        return self.tx.to_addr.get_address_str(self._address_format)

    @property
    def from_addr(self) -> str:
        return self.tx.from_addr.get_address_str(self._address_format)

    @property
    def explorer_url(self) -> str:
        return self.tx.explorer_url

    @property
    def nft_description(self) -> str:
        if self.tx.got_currency_is_nft:
            if not isinstance(self.tx.got_currency, HarmonyNFT):
                return ""

            return f" (got {self.tx.got_currency.full_name})"
        if self.tx.sent_currency_is_nft:
            if not isinstance(self.tx.sent_currency, HarmonyNFT):
                return ""

            return f" (sent {self.tx.sent_currency.full_name})"

        return ""
