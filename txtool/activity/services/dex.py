from typing import List
from decimal import Decimal

from txtool.harmony import (
    HarmonyToken,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class UniswapDexEditor(Editor):
    CONTRACT_ADDRESSES: List[str] = []
    _HANDLERS = {
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

        # zero out cost transaction
        root_tx.got_amount = Decimal(0)
        root_tx.sent_amount = Decimal(0)
        root_tx.coin_amount = Decimal(0)

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([root_tx, self.consolidate_trade(o, i)])
        )

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

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([root_tx, self.consolidate_trade(o, i)])
        )

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

        return InterpretedTransactionGroup(
            self.zero_non_root_cost([root_tx, self.consolidate_trade(o, i)])
        )

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
            self.zero_non_root_cost(
                [
                    # the root txc still holds the fee
                    root_tx,
                    self.consolidate_trade(send_1, receive_lp_tx_1),
                    self.consolidate_trade(send_2, receive_lp_tx_2),
                ]
            )
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
            self.zero_non_root_cost(
                [
                    # the root txc still holds the fee
                    root_tx,
                    self.consolidate_trade(send_1, receive_lp_tx_1),
                    self.consolidate_trade(send_2, receive_lp_tx_2),
                ]
            )
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
            self.zero_non_root_cost(
                [
                    root_tx,
                    self.consolidate_trade(lp_send_tx_1, get_1),
                    self.consolidate_trade(lp_send_tx_2, get_2),
                ]
            )
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
            self.zero_non_root_cost(
                [
                    root_tx,
                    self.consolidate_trade(lp_send_tx_1, get_1),
                    self.consolidate_trade(lp_send_tx_2, get_2),
                ]
            )
        )
