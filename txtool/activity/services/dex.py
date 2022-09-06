from typing import List, Tuple
from decimal import Decimal
from itertools import chain
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
        """
        Locking mechanism typically works by having 'MasterChef' contract send caller
        an amount of governance token. (got tx)

        During claims transaction, gov. token is minted from 0x0 or taken from
        xGovToken HRC20 contract (if that exists). These are all consolidated and
        sent to the 'MasterChef' contract, which then transfers all to the caller.

        After caller receives these tokens from the chef contract,
        the caller will send some portion of these tokens received in the plus
        transaction to the HRC20 contract of said tokens (sent tx). The number of
        tokens that are sent back is determined by the lock / emissions schedule.

        Example:
            - Caller calls Chef contract function 'claimRewards' or 'claimReward'
            - Chef gathers 100 GOV Token
            - Chef sends 100 GOV Token to caller
            - Caller receives 100 GOV Token
            - Caller sends 95 of GOV Token HRC20 Contract Address
            - by the end of the transaction, Caller is left with 5 GOV Token
                - this represents a 95% locked, 5% unlocked emission
        """
        consolidated_tx = deepcopy(next(x for x in claim_txs if x.is_receiver))

        got = sum(
            x.got_amount
            for x in claim_txs
            if x.is_receiver and x.got_currency_symbol == self.GOV_TOKEN_SYMBOL
        )
        sent = sum(
            x.sent_amount
            for x in claim_txs
            if x.is_sender and x.sent_currency_symbol == self.GOV_TOKEN_SYMBOL
        )

        delta = Decimal(got - sent)
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

        self._set_lp_token_pairs_from_trade(results)

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

        get_lp_tx_1, get_lp_tx_2 = self.split_copy(
            next(x for x in transactions[1:] if x.to_addr.eth == args["to"]),
            split_factor=2,
        )

        return InterpretedTransactionGroup(
            self.zero_non_root_cost(
                [
                    # the root txc still holds the fee
                    root_tx,
                    self.consolidate_trade_with_root(root_tx, send_1, get_lp_tx_1),
                    self.consolidate_trade_with_root(root_tx, send_2, get_lp_tx_2),
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

        lp_send_tx_1, lp_send_tx_2 = self.split_copy(
            next(x for x in transactions[1:] if x.from_addr.eth == root_tx.account.eth),
            split_factor=2,
        )

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

        lp_send_tx_1, lp_send_tx_2 = self.split_copy(
            next(x for x in transactions[1:] if x.from_addr.eth == root_tx.account.eth),
            split_factor=2,
        )

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

        self._set_lp_token_pairs_from_trade(results)

        return InterpretedTransactionGroup(results)

    def _extract_token_tx_pair_from_lp_token_txs(
        self, txs: List[WalletActivity]
    ) -> Tuple[HarmonyToken, HarmonyToken]:
        # find all non-LP tokens in given transactions
        # sort them based on universal symbol
        r = sorted(
            [
                x
                for x in set(chain(*[x.get_relevant_tokens() for x in txs]))
                if not x.is_lp_token
            ],
            key=lambda x: x.universal_symbol,
        )

        if len(r) != 2:
            raise RuntimeError(
                f"Trade mismatch... cannot find multiple non-LP tokens in transactions: {r}"
            )

        # alphabetical order
        lp_token_1, lp_token_2 = r
        return lp_token_1, lp_token_2

    def _set_lp_token_pairs_from_trade(self, txs: List[WalletActivity]) -> None:
        # if pair of LP token is not known, use this transaction to set
        # what the pair would be
        s = next((x for x in txs if x.sent_currency_is_lp_token), None)
        g = next((x for x in txs if x.got_currency_is_lp_token), None)
        base = s or g

        if not base:
            raise ValueError(f"Cannot determine LP tokens from transactions: {txs}")

        lpt = next(t for t in base.get_relevant_tokens() if t.is_lp_token)

        if not lpt.knows_lp_token_pairs:
            # always get transactions in alphabetical order by token symbol
            t_1, t_2 = self._extract_token_tx_pair_from_lp_token_txs(txs[1:])
            lpt.lp_token_0 = t_1
            lpt.lp_token_1 = t_2
