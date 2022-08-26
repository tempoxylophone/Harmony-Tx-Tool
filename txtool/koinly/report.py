from typing import Optional, Sequence, List

from txtool.csv.csv_creator import TransactionReportCreator
from txtool.csv.transaction_wrapper import TransactionCSVWrapper

from txtool.harmony import (
    HarmonyAddress,
    WalletActivity,
)


from .ruleset import (
    get_label_for_tx_and_description,
    is_cost,
    KOINLY_UNSUPPORTED_COIN_NAMES,
)


class KoinlyReportCreator(TransactionReportCreator):  # pylint: disable=R0902
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
    HEADER = [
        "Date",
        "Sent Amount",
        "Sent Currency",
        "Received Amount",
        "Received Currency",
        "Fee Amount",
        "Fee Currency",
        "Net Worth Amount",
        "Net Worth Currency",
        "Label",
        "Description",
        "TxHash",
        "Method",
        "To",
        "From",
        "Explorer URL",
        "\n",
    ]
    _KOINLY_TRACKED_CURRENCY_SYMBOLS = {
        "ONE",
        "ETH",
        "BTC",
        "USDT",
        "USDC",
        "DAI",
        "MATIC",
        "BNB",
        "SOL",
        "DOT",
        "AVAX",
        "LINK",
        "CRV",
    }

    def __init__(
        self,
        omit_cost: bool = True,
        date_lb_str: str = "",
        date_ub_str: str = "",
        tx_limit: Optional[int] = None,
    ) -> None:
        super().__init__(
            HarmonyAddress.FORMAT_ONE, True, date_lb_str, date_ub_str, tx_limit
        )
        self.omit_cost = omit_cost

    def get_wrapped_transactions(
        self, events: Sequence[WalletActivity]
    ) -> List[TransactionCSVWrapper]:
        if self.omit_cost:
            events = [x for x in events if not is_cost(x)]
        return super().get_wrapped_transactions(events)

    @staticmethod
    def currency_is_tracked(coin_symbol: str) -> bool:
        return (
            coin_symbol.upper() in KoinlyReportCreator._KOINLY_TRACKED_CURRENCY_SYMBOLS
        )

    def to_csv_row(self, tx: TransactionCSVWrapper) -> str:
        blank_fiat = self.omit_tracked_fiat_prices and self.currency_is_tracked(
            tx.coin_symbol
        )
        fiat_val = "" if blank_fiat else tx.net_worth_amount

        # koinly specific labels
        label, desc = get_label_for_tx_and_description(tx.tx)

        return ",".join(
            (
                # time of transaction
                tx.date,
                # block chain info
                tx.sent_amount,
                self.format_coin_symbol(tx.sent_currency),
                tx.got_amount,
                self.format_coin_symbol(tx.got_currency),
                tx.fee_amount,
                tx.fee_currency,
                # fiat info
                fiat_val,
                tx.net_worth_currency,
                # human readable stuff
                label,
                desc,
                # ID stuff
                tx.tx_hash,
                tx.method,
                tx.to_addr,
                tx.from_addr,
                tx.explorer_url,
                "\n",
            )
        )

    @staticmethod
    def format_coin_symbol(coin_symbol: str) -> str:
        if not coin_symbol:
            return coin_symbol

        # see if it should be replaced
        return KOINLY_UNSUPPORTED_COIN_NAMES.get(coin_symbol, coin_symbol)
