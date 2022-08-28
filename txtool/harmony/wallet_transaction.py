from __future__ import annotations
from typing import List, Optional, Union, Tuple, Dict
from enum import Enum
from decimal import Decimal
from copy import deepcopy

from eth_typing import HexStr
from web3.types import EventData

from txtool.dfk.constants import HARMONY_TOKEN_ADDRESS_MAP, DFK_PAYMENT_WALLET_ADDRESSES
from txtool.utils import MAIN_LOGGER

from .token import HarmonyToken, Token
from .api import HarmonyAPI
from .address import HarmonyAddress
from .transaction import HarmonyEVMTransaction


class WalletAction(str, Enum):
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    DONATION = "donation"
    WITHDRAWAL = "withdraw"
    NULL = ""


class WalletActivity(HarmonyEVMTransaction):  # pylint: disable=R0902
    def __init__(
        self,
        account: HarmonyAddress,
        tx_hash: HexStr,
        harmony_token: Optional[Token] = None,
    ):
        # get information about this tx
        super().__init__(account, tx_hash)

        # set custom token if it is given
        self.coin_type = harmony_token or self.coin_type
        self.reinterpret_action()

    @property
    def is_receiver(self) -> bool:
        return bool(self.to_addr == self.account)

    @property
    def is_sender(self) -> bool:
        return bool(self.from_addr == self.account)

    def _get_action(self) -> WalletAction:
        if self.is_receiver:
            return WalletAction.PAYMENT if self._is_payment() else WalletAction.DEPOSIT

        if self.is_sender:
            return (
                WalletAction.DONATION
                if self._is_donation()
                else WalletAction.WITHDRAWAL
            )

        # unknown
        return WalletAction.NULL

    def reinterpret_action(self) -> None:
        self.action = self._get_action()
        if self.action == WalletAction.DEPOSIT:
            # this wall got some currency
            self.sent_amount = Decimal(0)
            self.sent_currency = None
            self.got_amount = self.coin_amount
            self.got_currency = self.coin_type
        else:
            # this wallet sent some currency
            self.sent_amount = self.coin_amount
            self.sent_currency = self.coin_type
            self.got_amount = Decimal(0)
            self.got_currency = None

    def _is_payment(self) -> bool:
        return self.from_addr.eth in DFK_PAYMENT_WALLET_ADDRESSES

    def _is_donation(self) -> bool:
        return bool(self.to_addr) and "Donation" in HARMONY_TOKEN_ADDRESS_MAP.get(
            self.to_addr.eth, ""
        )

    @classmethod
    def extract_all_wallet_activity_from_transaction(
        cls,
        account: HarmonyAddress,
        tx_hash: Union[HexStr, str],
        exclude_intermediate_tx: Optional[bool] = True,
    ) -> List[WalletActivity]:
        root_tx = WalletActivity(account, HexStr(tx_hash))
        leaf_tx = WalletActivity._get_token_transfers(root_tx, exclude_intermediate_tx)
        return [root_tx, *leaf_tx]

    @staticmethod
    def _get_token_transfers(
        root_tx: WalletActivity, exclude_intermediate_tx: Optional[bool] = True
    ) -> List[WalletActivity]:
        receipt = root_tx.receipt

        transfers: List[WalletActivity] = []
        logs = list(HarmonyAPI.get_tx_transfer_logs(receipt))

        for i, log in enumerate(logs, start=1):
            # parse all transactions
            MAIN_LOGGER.info("\tExtracting sub-tx %s/%s...", i, len(logs))

            # in reverse order
            token_tx = WalletActivity._create_token_tx_from_log(root_tx, log, i)
            transfers.insert(0, token_tx)

        if WalletActivity._appears_to_be_bond_tx(root_tx):
            # there should be a tx where staking helper sends some amount of currency
            # as an IOU on stable coin.
            reserve_tx = next(
                x
                for x in transfers
                if
                # send to original contract
                x.to_addr == root_tx.to_addr and
                # but the thing sending it is not original wallet
                x.from_addr != root_tx.from_addr
            )

            if exclude_intermediate_tx:
                transfers = [
                    x for x in transfers if root_tx.account in (x.to_addr, x.from_addr)
                ]

            # preserve that IOU transaction
            return [*transfers, reserve_tx]

        if (
            WalletActivity._appears_to_be_uniswap_swap_tx(root_tx)
            or WalletActivity._appears_to_be_uniswap_remove_lp_tx(root_tx)
            or WalletActivity._has_uniswap_like_contract_token_interaction(
                root_tx, transfers
            )
        ):
            # root: You -> Contract
            # X -> Some LP -> Contract
            # 1: swap result: (Some LP -> Contract)
            # 0: give: (X -> Venom LP) [but it originally came from You]
            send_off = next(
                (
                    x
                    for x in transfers
                    if (
                        x.to_addr == root_tx.to_addr
                        and x.from_addr != root_tx.account
                        and x.from_addr.token
                        and x.from_addr.token.is_lp_token
                    )
                ),
                None,
            )
            original_transfer = send_off and next(
                (
                    x
                    for x in transfers
                    if (
                        x.to_addr == send_off.from_addr
                        and x.from_addr.token
                        and x.from_addr.token.is_lp_token
                    )
                ),
                None,
            )
            if original_transfer:
                original_transfer.from_addr = root_tx.account
                original_transfer.sent_amount = original_transfer.coin_amount
                original_transfer.sent_currency = original_transfer.coin_type

            # special handlers for Uniswap stuff
            transfers += WalletActivity._parse_uniswap_contract_debts(
                root_tx, transfers
            )

        if exclude_intermediate_tx:
            transfers = [
                x for x in transfers if root_tx.account in (x.to_addr, x.from_addr)
            ]

        return transfers

    @staticmethod
    def _has_uniswap_like_contract_token_interaction(
        root_tx: WalletActivity, transfers: List[WalletActivity]
    ) -> bool:
        # if there is a sub-tx that is an LP token transferring to the original contract
        # called by the caller, then this is likely a swap of some kind
        original_is_contract = root_tx.to_addr.belongs_to_non_token_smart_contract
        if not original_is_contract:
            return False

        # if any tokens came from an LP token contract and they are sent to the
        # originally called contract
        return bool(
            [
                x
                for x in transfers
                if (
                    x.from_addr.token
                    and x.from_addr.token.is_lp_token
                    and x.to_addr == root_tx.to_addr
                )
            ]
        )

    @staticmethod
    def _appears_to_be_uniswap_remove_lp_tx(root_tx: HarmonyEVMTransaction) -> bool:
        return "removeLiquidityETH" in root_tx.get_tx_function_signature()

    @staticmethod
    def _appears_to_be_uniswap_swap_tx(root_tx: HarmonyEVMTransaction) -> bool:
        if "swapExactTokensForETH" not in root_tx.get_tx_function_signature():
            return False

        decode_success, func_data = root_tx.tx_payload

        if not decode_success or not func_data:
            return False

        _, func_inputs = func_data
        did_call = func_inputs["to"] == root_tx.account.eth
        path_all_tokens = all(
            x.belongs_to_token for x in WalletActivity._get_uniswap_path(root_tx)
        )

        return did_call and path_all_tokens

    @staticmethod
    def _get_uniswap_path(
        root_tx: HarmonyEVMTransaction,
    ) -> Tuple[HarmonyAddress, HarmonyAddress]:
        decode_success, func_data = root_tx.tx_payload

        if not decode_success or not func_data:
            raise ValueError(
                "Transaction that appeared to be Uniswap swap could not be decoded"
            )

        _, func_inputs = func_data
        address_from = func_inputs["path"][0]
        address_to = func_inputs["path"][-1]

        return (
            HarmonyAddress.get_harmony_address(address_from),
            HarmonyAddress.get_harmony_address(address_to),
        )

    @staticmethod
    def _parse_uniswap_contract_debts(
        root_tx: WalletActivity, transfers: List[WalletActivity]
    ) -> List[WalletActivity]:
        contract_debts = [x for x in transfers if x.to_addr == root_tx.to_addr]
        parsed_debts = []

        for d in contract_debts:
            # wallet originally called uniswap contract
            if [
                x
                for x in transfers
                if x.to_addr == root_tx.account and x.coin_type == d.coin_type
            ]:
                # tx already exists
                continue

            # create tx that is the contract sending you what you requested
            return_tx = WalletActivity(
                # technically this is not the same hash, but we want it to show up
                root_tx.account,
                root_tx.tx_hash,
                d.coin_type,
            )
            return_tx.to_addr = root_tx.account
            return_tx.from_addr = root_tx.to_addr

            return_tx.coin_amount = d.coin_amount
            return_tx.got_amount = d.coin_amount
            return_tx.got_currency = d.coin_type
            return_tx.is_token_transfer = True

            parsed_debts.append(return_tx)

        return parsed_debts

    @staticmethod
    def _appears_to_be_bond_tx(root_tx: WalletActivity) -> bool:
        # rebase token / OHM-like transaction for bond
        return (
            root_tx.method == "deposit(uint256,uint256,address)"
            and
            # Euphoria BondDepository contract
            root_tx.to_addr.eth == "0x202c598E93F69dbe3a5e5706DfB85bdc598bb16F"
        )

    @staticmethod
    def _create_token_tx_from_log(
        root_tx: WalletActivity, log: EventData, log_idx: int
    ) -> WalletActivity:
        token = HarmonyToken.get_harmony_token_by_address(log["address"])
        value = token.get_value_from_wei(log["args"]["value"])

        r = WalletActivity(root_tx.account, root_tx.tx_hash, token)
        r.log_idx = log_idx
        r.coin_amount = value
        r.event = log["event"]
        r.is_token_transfer = r.event == "Transfer"

        # logs can be different from root transaction - must set them here
        r.to_addr = HarmonyToken.get_address_and_set_token(log["args"]["to"])
        r.from_addr = HarmonyToken.get_address_and_set_token(log["args"]["from"])
        r.reinterpret_action()

        return r

    def __copy__(self) -> WalletActivity:
        new_tx = WalletActivity(self.account, self.tx_hash, self.coin_type)
        new_tx.__dict__.update(self.__dict__)
        return new_tx

    def __deepcopy__(self, memo: Dict) -> WalletActivity:
        self_module: str = self.__class__.__module__.rsplit(".", 1)[0]

        # create a copy of this transaction, set all important fields
        wallet_copy = WalletActivity(self.account, self.tx_hash, self.coin_type)
        memo[id(self)] = wallet_copy

        for attr_name, attr in self.__dict__.items():
            cls_module: str = attr.__class__.__module__.rsplit(".", 1)[0]
            v = attr
            if cls_module != self_module:
                # actually copy other stuff
                v = deepcopy(attr)
            setattr(wallet_copy, attr_name, v)

        return wallet_copy

    def __str__(self) -> str:  # pragma: no cover
        return "tx: {0} --[{1} {2}]--> {3} ({4}) - log idx = {5}".format(
            self.from_addr.eth,
            self.coin_amount,
            self.coin_type and self.coin_type.symbol or "(NULL COIN TYPE)",
            self.to_addr.eth,
            self.tx_hash,
            self.log_idx,
        )
