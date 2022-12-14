from typing import List, Optional
from decimal import Decimal

from txtool.harmony import (
    HarmonyEVMSmartContract,
    HarmonyAPI,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class TranquilFinanceStakingEditor(Editor):
    CONTRACT_ADDRESSES = [
        # TranquilStakingProxy
        "0xA7Fe71bC92d3A48aC59403b9be86f73e49bfCd46",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "redeem(uint256)":
            return self.parse_redeem(transactions)
        if root_method == "claimRewards()":
            return self.parse_claim_rewards(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_redeem(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # unstaking
        return InterpretedTransactionGroup(self.zero_non_root_cost(transactions))

    def parse_claim_rewards(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(self.zero_non_root_cost(transactions))


class TranquilFinanceONEDepositEditor(Editor):
    HRC20_TQ_ONE_ADDR_STR = "0x34B9aa82D89AE04f0f546Ca5eC9C93eFE1288940"
    HRC20_STONE_ADDR_STR = "0x22D62b19b7039333ad773b7185BB61294F3AdC19"
    CONTRACT_ADDRESSES = [
        # TRANQ HRC20 (tqONE)
        HRC20_TQ_ONE_ADDR_STR,
        # Unknown ABI
        "0x0ff9a77212609FE8fF8B1C85E60FCa66aDDaC045",
        # Unknown ABI
        "0xDE010f117000Ed4037de1c199b3F371FEd5B12C7",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)
        self._redeem_contract: Optional[HarmonyEVMSmartContract] = None

    @property
    def redeem_decoding_contract(self) -> HarmonyEVMSmartContract:
        if self._redeem_contract is None:
            self._redeem_contract = (
                HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(
                    self.HRC20_TQ_ONE_ADDR_STR
                )
            )

        if not isinstance(self._redeem_contract, HarmonyEVMSmartContract):
            raise RuntimeError(
                f"Could not decode contract at address: {self.HRC20_TQ_ONE_ADDR_STR}"
            )

        return self._redeem_contract

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "redeem(uint256)":
            return self.parse_redeem(transactions)
        if root_method == "mint()":
            return self.parse_mint(transactions)
        if root_method == "deposit(uint256)":
            return self.parse_deposit(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_mint(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # deposit ONE to tranquil, get tqONE in return
        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [self.consolidate_trade(transactions[0], transactions[1])]
            )
        )

    def parse_redeem(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) == 3:
            get_tx = transactions[1]
            give_tx = transactions[2]
            return InterpretedTransactionGroup(
                self.zero_non_root_cost(
                    [transactions[0], self.consolidate_trade(give_tx, get_tx)]
                )
            )
        if len(transactions) == 2:
            # a bit different, the way the reimbursement of ONE tokens is
            # handled is not in a transfer event, so we need to fetch parameters
            # of that through a 'Redeem' event
            cost_tx = transactions[0]

            trade_tx = transactions[1]

            redeem_event = self.redeem_decoding_contract.get_tx_logs_by_event_name(
                cost_tx.tx_hash, "Redeem"
            )[0]

            args = redeem_event["args"]

            one_token = cost_tx.coin_type.get_native_token()
            one_received_amount = HarmonyAPI.get_value_from_wei(
                args["redeemAmount"], one_token.decimals
            )

            # edit transaction
            trade_tx.got_amount = one_received_amount
            trade_tx.got_currency = one_token
            trade_tx.to_addr = cost_tx.to_addr
            trade_tx.from_addr = cost_tx.account

            return InterpretedTransactionGroup(
                self.zero_non_root_cost([cost_tx, trade_tx])
            )

        # does not apply
        return InterpretedTransactionGroup(transactions)

    def parse_deposit(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        if len(transactions) == 3:
            # ONE -> stONE
            o = transactions[0]
            i = next(x for x in transactions if x.is_receiver)
            return InterpretedTransactionGroup([self.consolidate_trade(o, i)])

        # doesn't apply here
        return InterpretedTransactionGroup(transactions)


class TranquilFinanceEditor(Editor):
    CONTRACT_ADDRESSES = [
        # Unitroller
        "0x6a82A17B48EF6be278BBC56138F35d04594587E3",
        # TqErc20Delegator
        "0x7af2430eFa179dB0e76257E5208bCAf2407B2468",
        # TqErc20Delegator (2)
        "0xCa3e902eFdb2a410C952Fd3e4ac38d7DBDCB8E96",
        # TqErc20Delegator (3)
        "0xc63AB8c72e636C9961c5e9288b697eC5F0B8E1F7",
        # TqErc20Delegator (4)
        "0x973f22036A0fF3A93654e7829444ec64CB37BD78",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method
        if root_method == "claimReward(uint8,address)":
            return self.parse_claim_reward(transactions)
        if root_method == "mint(uint256)":
            return self.parse_mint(transactions)
        if root_method == "redeem(uint256)":
            return self.parse_redeem(transactions)
        if root_method == "borrow(uint256)":
            return self.parse_borrow(transactions)
        if root_method == "repayBorrow(uint256)":
            return self.parse_repay_borrow(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_claim_reward(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        reward_tx = transactions[1]
        reward_tx.got_amount = Decimal(
            sum(x.got_amount for x in transactions[1:] if x.is_receiver) or 0
        )
        return InterpretedTransactionGroup(
            self.zero_non_root_cost([transactions[0], reward_tx])
        )

    def parse_mint(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_tx = transactions[0]
        get_tx = next(x for x in transactions[1:] if x.to_addr == root_tx.account)
        give_tx = next(x for x in transactions[1:] if x.from_addr == root_tx.account)
        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [transactions[0], self.consolidate_trade(give_tx, get_tx)]
            )
        )

    def parse_redeem(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        get_tx = transactions[1]
        give_tx = transactions[2]
        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [transactions[0], self.consolidate_trade(give_tx, get_tx)]
            )
        )

    def parse_borrow(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(self.zero_non_root_cost(transactions))

    def parse_repay_borrow(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        return InterpretedTransactionGroup(self.zero_non_root_cost(transactions))


TRANQUIL_DEPOSIT_COLLATERAL_ADDRESSES = [
    *TranquilFinanceEditor.CONTRACT_ADDRESSES,
    *TranquilFinanceONEDepositEditor.CONTRACT_ADDRESSES,
]
TRANQUIL_COLLECT_REWARD_ADDRESSES = [
    # unitroller address
    TranquilFinanceEditor.CONTRACT_ADDRESSES[0],
    # staking contract addresses
    *TranquilFinanceStakingEditor.CONTRACT_ADDRESSES,
]
