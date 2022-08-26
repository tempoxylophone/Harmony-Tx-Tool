from typing import List
from copy import deepcopy

from txtool.harmony import (
    HarmonyToken,
    HarmonyPlaceholderToken,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class EuphoriaBondEditor(Editor):
    WAGMI_TOKEN = HarmonyToken.get_harmony_token_by_address(
        "0x0dc78c79B4eB080eaD5C1d16559225a46b580694"
    )

    # not a real currency, used for book-keeping purposes
    bWAGMI_TOKEN = HarmonyPlaceholderToken(
        WAGMI_TOKEN, "bondIOUWAGMI", "bWAGMI", "0xbWAGMIAddress"
    )
    CONTRACT_ADDRESSES = [
        # BondDepositories
        "0x202c598E93F69dbe3a5e5706DfB85bdc598bb16F",
        "0xF43911c859532E38c969ee1b59Eeca3De5630Fe3",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_tx = transactions[0]

        if root_tx.method == "deposit(uint256,uint256,address)":
            return self.interpret_bond(transactions)
        if root_tx.method == "redeem(address,bool)":
            return self.interpret_redeem(transactions)

        # can't interpret this
        return InterpretedTransactionGroup(transactions)

    def interpret_bond(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) != 3:
            # don't interpret this
            return InterpretedTransactionGroup(transactions)

        root_tx = transactions[0]
        send_tx = transactions[1]

        # find the transaction where the original contract was the
        # recipient of some amount of WAGMI
        iou_tx = next(
            x
            for x in transactions
            if x.to_addr_str == self.CONTRACT_ADDRESSES[0]
            and x.coin_type == self.WAGMI_TOKEN
        )

        # edit this transaction so that the original contract sends
        # that WAGMI to original caller
        iou_tx.from_addr = iou_tx.to_addr
        iou_tx.to_addr = root_tx.from_addr

        # instead of sending WAGMI, we need to send some placeholder or proxy
        # for that amount in the future
        iou_tx.coin_type = self.bWAGMI_TOKEN
        iou_tx.got_currency = self.bWAGMI_TOKEN
        iou_tx.got_amount = iou_tx.coin_amount

        return InterpretedTransactionGroup([root_tx, iou_tx, send_tx])

    def interpret_redeem(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) != 2 or transactions[1].got_currency_symbol not in (
            "WAGMI",
            "sWAGMI",
        ):
            # can't interpret this
            return InterpretedTransactionGroup(transactions)

        root_tx = transactions[0]
        get_tx = transactions[1]

        # create a send transaction as if you sent bWAGMI for WAGMI or sWAGMI
        send_tx = deepcopy(root_tx)
        send_tx.coin_type = self.bWAGMI_TOKEN
        send_tx.sent_currency = self.bWAGMI_TOKEN
        send_tx.coin_amount = get_tx.coin_amount
        send_tx.sent_amount = get_tx.got_amount

        return InterpretedTransactionGroup(
            [
                root_tx,
                get_tx,
                send_tx,
            ]
        )
