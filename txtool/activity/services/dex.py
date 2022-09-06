from typing import List
from decimal import Decimal
from copy import deepcopy

from txtool.harmony import (
    HarmonyToken,
    WalletActivity,
)
from .common import Editor, InterpretedTransactionGroup


class MasterChefDexEditor(Editor):
    # anything that looks like this:
    # https://github.com/sushiswap/sushiswap/blob/913076f9c02b8f3bc0d2dfefb59853d86d6e9e17/contracts/MasterChef.sol
    CONTRACT_ADDRESSES: List[str] = []
    GOV_TOKEN_SYMBOL = ""
    LP_TOKEN_SYMBOL_PREFIX = ""
    _HANDLERS = {
        "deposit(uint256,uint256,address)": "parse_deposit",
        "claimRewards(uint256[])": "parse_claim_reward",
        "claimReward(uint256)": "parse_claim_reward",
        "withdraw(uint256,uint256,address)": "parse_withdraw",
    }
    METHODS = list(_HANDLERS)  # keys only

    def parse_withdraw(
        self, transactions: List[WalletActivity]
    ) -> InterpretedTransactionGroup:
        relevant_txs = [x for x in transactions if x.is_sender or x.is_receiver]

        cost_tx = relevant_txs[0]
        claims_tx = [
            x for x in relevant_txs if x.coin_type.symbol == self.GOV_TOKEN_SYMBOL
        ]
        lp_get = next(
            x
            for x in relevant_txs
            if x.got_currency_symbol.startswith(self.LP_TOKEN_SYMBOL_PREFIX)
        )

        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [cost_tx, self._consolidate_claims(claims_tx), lp_get]
            )
        )

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
            x
            for x in claim_txs
            if x.is_receiver and x.got_currency_symbol == self.GOV_TOKEN_SYMBOL
        ]
        minus_tx = [
            x
            for x in claim_txs
            if x.is_sender and x.got_currency_symbol == self.GOV_TOKEN_SYMBOL
        ]

        consolidated_tx = deepcopy(plus_tx[0])

        delta = Decimal(
            sum(x.got_amount for x in plus_tx) + sum(x.sent_amount for x in minus_tx)
        )
        consolidated_tx.coin_amount = delta
        consolidated_tx.got_amount = delta

        return consolidated_tx


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
        root_tx = self.zero_root_amounts(root_tx)

        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [
                    root_tx,
                    self.consolidate_trade_with_root(root_tx, o, i),
                ]
            )
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
            self.zero_non_root_cost(
                [root_tx, self.consolidate_trade_with_root(root_tx, o, i)]
            )
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
            self.zero_non_root_cost(
                [root_tx, self.consolidate_trade_with_root(root_tx, o, i)]
            )
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
        root_tx = self.zero_root_amounts(root_tx)
        results = self.zero_non_root_cost(
            [
                # the root txc still holds the fee
                root_tx,
                self.consolidate_trade_with_root(root_tx, send_1, receive_lp_tx_1),
                self.consolidate_trade_with_root(root_tx, send_2, receive_lp_tx_2),
            ]
        )

        # if pair of LP token is not known, use this transaction to set
        # what the pair would be
        lp_token = receive_lp_tx_1.coin_type

        if not isinstance(lp_token, HarmonyToken):
            raise RuntimeError(f"TX: {root_tx} got invalid LP Token: {lp_token}")

        if not (lp_token.lp_token_0 and lp_token.lp_token_1):
            # always get transactions in alphabetical order by token symbol
            lp_tx_1, lp_tx_2 = sorted(
                results[1:],
                key=lambda x: x.sent_currency
                and x.sent_currency.universal_symbol
                or "",
            )

            if not (
                isinstance(lp_tx_2.sent_currency, HarmonyToken)
                and isinstance(lp_tx_1.sent_currency, HarmonyToken)
            ):
                raise RuntimeError(
                    "TX: {0} got invalid LP Token Pairs: ({1}/{2})".format(
                        root_tx, lp_tx_1.sent_currency, lp_tx_2.sent_currency
                    )
                )

            lp_token.lp_token_0 = lp_tx_1.sent_currency
            lp_token.lp_token_1 = lp_tx_2.sent_currency

        return InterpretedTransactionGroup(results)

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
                    self.consolidate_trade_with_root(root_tx, send_1, receive_lp_tx_1),
                    self.consolidate_trade_with_root(root_tx, send_2, receive_lp_tx_2),
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
                    self.consolidate_trade_with_root(root_tx, lp_send_tx_1, get_1),
                    self.consolidate_trade_with_root(root_tx, lp_send_tx_2, get_2),
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

        results = self.zero_non_root_cost(
            [
                root_tx,
                self.consolidate_trade_with_root(root_tx, lp_send_tx_1, get_1),
                self.consolidate_trade_with_root(root_tx, lp_send_tx_2, get_2),
            ]
        )

        # if pair of LP token is not known, use this transaction to set
        # what the pair would be
        lp_token = lp_send_tx_1.coin_type
        if not isinstance(lp_token, HarmonyToken):
            raise RuntimeError(f"TX: {root_tx} got invalid LP Token: {lp_token}")

        if not (lp_token.lp_token_0 and lp_token.lp_token_1):
            # always get transactions in alphabetical order by token symbol
            lp_tx_1, lp_tx_2 = sorted(
                results[1:],
                key=lambda x: x.got_currency and x.got_currency.universal_symbol or "",
            )

            if not (
                isinstance(lp_tx_2.got_currency, HarmonyToken)
                and isinstance(lp_tx_1.got_currency, HarmonyToken)
            ):
                raise RuntimeError(
                    "TX: {0} got invalid LP Token Pairs: ({1}/{2})".format(
                        root_tx, lp_tx_1.got_currency, lp_tx_2.got_currency
                    )
                )

            lp_token.lp_token_0 = lp_tx_1.got_currency
            lp_token.lp_token_1 = lp_tx_2.got_currency

        return InterpretedTransactionGroup(results)
