from typing import List, Optional
from copy import deepcopy

from txtool.harmony import (
    HarmonyToken,
    HarmonyPlaceholderToken,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class EuphoriaWrapEditor(Editor):
    CONTRACT_ADDRESSES = [
        # HRC20 - wsWAGMI
        "0xBb948620Fa9cD554eF9A331B13eDeA9B181F9D45",
    ]
    HRC_20_WSWAGMI = "0xBb948620Fa9cD554eF9A331B13eDeA9B181F9D45"
    HRC_20_SWAGMI = "0xF38593388079F7f5130d605E38aBF6090D981eC2"

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "wrap(uint256)":
            return self.parse_wrap(transactions)
        if root_method == "unwrap(uint256)":
            return self.parse_unwrap(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_wrap(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        cost_tx = transactions[0]
        o, i = self.get_pair_by_address(
            transactions, self.HRC_20_SWAGMI, self.HRC_20_WSWAGMI
        )

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([cost_tx, self.consolidate_trade(o, i)])
        )

    def parse_unwrap(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        cost_tx = transactions[0]
        o, i = self.get_pair_by_address(
            transactions, self.HRC_20_WSWAGMI, self.HRC_20_SWAGMI
        )

        # overwrite null address
        o.to_addr = cost_tx.to_addr

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([cost_tx, self.consolidate_trade(o, i)])
        )


class EuphoriaBondEditor(Editor):
    WAGMI_TOKEN_ADDR_STR = "0x0dc78c79B4eB080eaD5C1d16559225a46b580694"
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
        self._wagmi_token: Optional[HarmonyToken] = None
        self._bwagmi_token: Optional[HarmonyPlaceholderToken] = None

    @property
    def WAGMI_TOKEN(self) -> HarmonyToken:
        if self._wagmi_token is None:
            self._wagmi_token = HarmonyToken.get_harmony_token_by_address(
                self.WAGMI_TOKEN_ADDR_STR
            )

        if not isinstance(self._wagmi_token, HarmonyToken):
            raise RuntimeError(
                f"Could not load WAGMI Token (address: {self.WAGMI_TOKEN_ADDR_STR})"
            )

        return self._wagmi_token

    @property
    def bWAGMI_TOKEN(self) -> HarmonyPlaceholderToken:
        if self._bwagmi_token is None:
            self._bwagmi_token = HarmonyPlaceholderToken(
                self.WAGMI_TOKEN, "bondIOUWAGMI", "bWAGMI", "0xbWAGMIAddress"
            )

        if not isinstance(self._bwagmi_token, HarmonyPlaceholderToken):
            raise RuntimeError(
                f"Could not load bWAGMI Token (address: {self.WAGMI_TOKEN_ADDR_STR})"
            )

        return self._bwagmi_token

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
            self.zero_non_root_cost(
                [transactions[0], self.consolidate_trade(give_tx, get_tx)]
            )
        )

    def parse_unstake(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        give_tx = transactions[1]
        get_tx = transactions[-1]
        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [transactions[0], self.consolidate_trade(give_tx, get_tx)]
            )
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
            if x.to_addr_str in self.CONTRACT_ADDRESSES
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
            self.zero_non_root_cost(
                [
                    root_tx,
                    self.consolidate_trade(send_tx, iou_tx),
                ]
            )
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
            self.zero_non_root_cost(
                [
                    root_tx,
                    self.consolidate_trade(send_tx, get_tx),
                ]
            )
        )
