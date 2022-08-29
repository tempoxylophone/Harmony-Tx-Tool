from typing import List, Callable
from decimal import Decimal
from copy import deepcopy

from txtool.harmony import (
    HarmonyToken,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class ViperSwapClaimRewardsEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Viper Rewards Contract
        "0x7AbC67c8D4b248A38B0dc5756300630108Cb48b4",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "deposit(uint256,uint256,address)":
            return self.parse_deposit(transactions)

        if root_method in ("claimRewards(uint256[])", "claimReward(uint256)"):
            return self.parse_claim_reward(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_deposit(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # add liquidity and claim rewards
        # everything after the first two is some kind of claim reward
        # when you enter an LP position you had already entered, when
        # you stake the position, you automatically claim rewards
        deposit_tx = transactions[-1]
        results = [
            transactions[0],
            deposit_tx,
        ]

        claim_txs = [x for x in transactions[1:-1] if x.is_sender or x.is_receiver]
        if claim_txs:
            results.append(self._consolidate_claims(claim_txs))

        return InterpretedTransactionGroup(results)

    def parse_claim_reward(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # claim rewards only
        return InterpretedTransactionGroup(
            [transactions[0], self._consolidate_claims(transactions[1:])]
        )

    def _consolidate_claims(self, claim_txs: List[WalletActivity]) -> WalletActivity:
        plus_tx = [
            x for x in claim_txs if x.is_receiver and x.got_currency_symbol == "VIPER"
        ]
        minus_tx = [
            x for x in claim_txs if x.is_sender and x.got_currency_symbol == "VIPER"
        ]

        consolidated_tx = deepcopy(plus_tx[0])

        delta = Decimal(
            sum(x.got_amount for x in plus_tx) + sum(x.sent_amount for x in minus_tx)
        )
        consolidated_tx.coin_amount = delta
        consolidated_tx.got_amount = delta

        return consolidated_tx


class ViperSwapXRewardsEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap ViperPit
        "0x08913d353091e24B361f0E519e2f7aD07a78995d",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method

        if root_method == "convertMultiple(address[],address[])":
            return self.parse_convert_multiple(transactions)

        return InterpretedTransactionGroup(transactions)

    def parse_convert_multiple(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # ignore everything after initial contract call
        return InterpretedTransactionGroup([transactions[0]])


class ViperSwapLiquidityEditor(Editor):
    CONTRACT_ADDRESSES = [
        # ViperSwap Uniswap Router v2 Contract
        "0xf012702a5f0e54015362cBCA26a26fc90AA832a3",
        # HRC20 ViperPit (xVIPER)
        "0xE064a68994e9380250CfEE3E8C0e2AC5C0924548",
    ]
    XVIPER_HRC20_ADDRESS = "0xE064a68994e9380250CfEE3E8C0e2AC5C0924548"
    VIPER_HRC20_ADDRESS = "0xEa589E93Ff18b1a1F1e9BaC7EF3E86Ab62addc79"
    _HANDLERS = {
        # enter viperpit
        "enter(uint256)": "parse_enter",
        # exit viperpit
        "leave(uint256)": "parse_leave",
        # swap tokens for eth
        "swapExactTokensForETH(uint256,uint256,address[],address,"
        "uint256)": "parse_swap_exact_tokens_for_eth",
        # swap eth for tokens
        "swapExactETHForTokens(uint256,address[],"
        "address,uint256)": "parse_swap_exact_eth_for_tokens",
        # swap tokens for tokens
        "swapExactTokensForTokens(uint256,uint256,address[],address,"
        "uint256)": "parse_swap_exact_tokens_for_tokens",
        # add liquidity
        "addLiquidity(address,address,uint256,uint256,uint256,"
        "uint256,address,uint256)": "parse_add_liquidity",
        # add liquidity eth
        "addLiquidityETH(address,uint256,uint256,uint256,address,"
        "uint256)": "parse_add_liquidity_eth",
        # remove liquidity
        "removeLiquidity(address,address,uint256,uint256,uint256,"
        "address,uint256)": "parse_remove_liquidity",
        # remove liquidity eth
        "removeLiquidityETH(address,uint256,uint256,uint256,"
        "address,uint256)": "parse_remove_liquidity_eth",
    }

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)

    def interpret(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        root_method = transactions[0].method
        f: Callable[[List[WalletActivity]], InterpretedTransactionGroup] = (
            # give transactions to appropriate handler
            getattr(self, self._HANDLERS[root_method])
            if root_method in self._HANDLERS
            else
            # do nothing, just cast
            InterpretedTransactionGroup
        )
        return f(transactions)

    def parse_enter(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # VIPER -> xVIPER
        root_tx = transactions[0]

        o, i = self.get_pair_by_address(
            transactions, self.VIPER_HRC20_ADDRESS, self.XVIPER_HRC20_ADDRESS
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])

    def parse_leave(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        # xVIPER -> VIPER
        root_tx = transactions[0]

        o, i = self.get_pair_by_address(
            transactions, self.XVIPER_HRC20_ADDRESS, self.VIPER_HRC20_ADDRESS
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])

    def parse_swap_exact_eth_for_tokens(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#swapexactethfortokens
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        o, i = self.get_pair_by_address(
            transactions,
            args["path"][0],
            args["path"][-1],
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])

    def parse_swap_exact_tokens_for_eth(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#swapexacttokensforeth
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        # get only the edges of the path
        o, i = self.get_pair_by_address(
            transactions,
            args["path"][0],
            args["path"][-1],
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])

    def parse_swap_exact_tokens_for_tokens(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#swapexacttokensfortokens
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        # get only the edges of the path
        o, i = self.get_pair_by_address(
            transactions,
            args["path"][0],
            args["path"][-1],
        )

        return InterpretedTransactionGroup([root_tx, self.consolidate_trade(o, i)])

    def parse_add_liquidity_eth(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#addliquidityeth
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        addr_1 = args["token"]
        addr_2 = HarmonyToken.get_native_token_eth_address_str()

        send_1, send_2 = self.get_pair_by_address(
            transactions,
            addr_1,
            addr_2,
        )

        receive_lp_tx_1 = next(
            x for x in transactions[1:] if x.to_addr.eth == args["to"]
        )
        receive_lp_tx_1, receive_lp_tx_2 = self.split_copy(receive_lp_tx_1, 2)

        # root transaction over-counts what you added to LP
        root_tx.coin_amount = Decimal(0)
        root_tx.sent_amount = Decimal(0)
        root_tx.got_amount = Decimal(0)

        return InterpretedTransactionGroup(
            [
                # the root txc still holds the fee
                root_tx,
                self.consolidate_trade(send_1, receive_lp_tx_1),
                self.consolidate_trade(send_2, receive_lp_tx_2),
            ]
        )

    def parse_add_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#addliquidity
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        send_1, send_2 = self.get_pair_by_address(
            transactions, args["tokenA"], args["tokenB"]
        )

        receive_lp_tx_1 = next(
            x for x in transactions[1:] if x.to_addr.eth == args["to"]
        )
        receive_lp_tx_1, receive_lp_tx_2 = self.split_copy(receive_lp_tx_1, 2)

        return InterpretedTransactionGroup(
            [
                # the root txc still holds the fee
                root_tx,
                self.consolidate_trade(send_1, receive_lp_tx_1),
                self.consolidate_trade(send_2, receive_lp_tx_2),
            ]
        )

    def parse_remove_liquidity(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#removeliquidity
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        lp_send_tx_1 = next(
            x for x in transactions[1:] if x.from_addr.eth == root_tx.account.eth
        )
        lp_send_tx_1, lp_send_tx_2 = self.split_copy(lp_send_tx_1, 2)

        get_1, get_2 = self.get_pair_by_address(
            transactions, args["tokenA"], args["tokenB"]
        )

        return InterpretedTransactionGroup(
            [
                root_tx,
                self.consolidate_trade(lp_send_tx_1, get_1),
                self.consolidate_trade(lp_send_tx_2, get_2),
            ]
        )

    def parse_remove_liquidity_eth(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        """
        https://docs.uniswap.org/protocol/V2/reference/smart-contracts/router-02#removeliquidityeth
        """
        root_tx = transactions[0]
        args = self.get_root_tx_input(transactions)

        lp_send_tx_1 = next(
            x for x in transactions[1:] if x.from_addr.eth == root_tx.account.eth
        )
        lp_send_tx_1, lp_send_tx_2 = self.split_copy(lp_send_tx_1, 2)

        token_1_address = args["token"]
        token_2_address = HarmonyToken.get_native_token_eth_address_str()
        get_1, get_2 = self.get_pair_by_address(
            transactions, token_1_address, token_2_address
        )

        return InterpretedTransactionGroup(
            [
                root_tx,
                self.consolidate_trade(lp_send_tx_1, get_1),
                self.consolidate_trade(lp_send_tx_2, get_2),
            ]
        )
