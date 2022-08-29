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
        # Staking Helper
        "0xEc6c0B83410c732Ac41Ee8391e35A4fcb0dcc799",
        # Staking
        "0x95066025af40F7f7832f61422802cD1e13C23753",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "deposit(uint256,uint256,address)":
            return self.parse_deposit(transactions)
        if root_method == "redeem(address,bool)":
            return self.parse_redeem(transactions)
        if root_method == "stake(uint256,address)":
            return self.parse_stake(transactions)
        if root_method == "unstake(uint256,bool)":
            return self.parse_unstake(transactions)

        # can't interpret this
        return InterpretedTransactionGroup(transactions)

    def parse_stake(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        give_tx = transactions[1]
        get_tx = transactions[-1]
        return InterpretedTransactionGroup(
            [transactions[0], self.consolidate_trade(give_tx, get_tx)]
        )

    def parse_unstake(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        give_tx = transactions[1]
        get_tx = transactions[-1]
        return InterpretedTransactionGroup(
            [transactions[0], self.consolidate_trade(give_tx, get_tx)]
        )

    def parse_deposit(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
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

        return InterpretedTransactionGroup(
            [
                root_tx,
                self.consolidate_trade(send_tx, iou_tx),
            ]
        )

    def parse_redeem(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        stake = args["_stake"]
        coin_type_got = "sWAGMI" if stake else "WAGMI"
        get_tx = next(x for x in transactions if x.got_currency_symbol == coin_type_got)

        # create a send transaction as if you sent bWAGMI for WAGMI or sWAGMI
        send_tx = deepcopy(root_tx)
        send_tx.coin_type = self.bWAGMI_TOKEN
        send_tx.coin_amount = get_tx.coin_amount

        return InterpretedTransactionGroup(
            [
                root_tx,
                self.consolidate_trade(send_tx, get_tx),
            ]
        )
