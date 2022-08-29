from __future__ import annotations
from typing import Dict, Union, Optional
from decimal import Decimal

from .constants import (
    NATIVE_TOKEN_ETH_ADDRESS_STR,
    NATIVE_TOKEN_SYMBOL,
)
from .api import HarmonyAPI
from .address import HarmonyAddress
from .abc import Token

from ..dex import UniswapV2ForkGraph
from .constants import VIPERSWAP_GRAPH_CONFIG


class HarmonyToken(Token):  # pylint: disable=R0902
    _TOKEN_DIRECTORY: Dict[HarmonyAddress, HarmonyToken] = {}
    _VIPERSWAP = UniswapV2ForkGraph(*VIPERSWAP_GRAPH_CONFIG)

    def __init__(
        self,
        address: Union[str, HarmonyAddress],
        merge_one_wone_names: Optional[bool] = True,
    ):
        super().__init__(address)
        self.address = HarmonyAddress.get_harmony_address(address)
        self.address.belongs_to_token = True
        self.address.token = self

        symbol, decimals, name = HarmonyAPI.get_token_info(self.address.eth)
        self.name = name
        self.symbol = symbol
        self.decimals = decimals

        # DEX stuff
        self.is_lp_token = False
        self.lp_token_0: Union[HarmonyToken, None] = None
        self.lp_token_1: Union[HarmonyToken, None] = None

        if self.symbol == "WONE":
            # consider WONE and ONE equivalent by symbol
            if merge_one_wone_names:
                self.symbol = NATIVE_TOKEN_SYMBOL
        else:
            # if not a native currency, try to see if it an LP position
            self._set_is_lp_token_guess()

        # add self to directory for later
        HarmonyToken._TOKEN_DIRECTORY[self.address] = self

    @classmethod
    def clear_directory(cls) -> None:
        cls._TOKEN_DIRECTORY = {}

    @classmethod
    def get_native_token(cls) -> HarmonyToken:
        return cls.get_harmony_token_by_address(NATIVE_TOKEN_ETH_ADDRESS_STR)

    @classmethod
    def get_native_token_eth_address_str(cls) -> str:
        return NATIVE_TOKEN_ETH_ADDRESS_STR

    @property
    def is_native_token(self) -> bool:
        return bool(self.address.eth == NATIVE_TOKEN_ETH_ADDRESS_STR)

    @classmethod
    def get_address_and_set_token(cls, eth_address_str: str) -> HarmonyAddress:
        addr_obj = HarmonyAddress.get_harmony_address(eth_address_str)
        if addr_obj.belongs_to_token:
            token = HarmonyToken.get_harmony_token_by_address(addr_obj)
            addr_obj.token = token

        return addr_obj

    def _set_is_lp_token_guess(self) -> None:
        dex_info = self._VIPERSWAP.get_token_or_pair_info(self.address.eth)

        if not dex_info:
            # cannot get API response - guess based on the name
            # can't retrieve pairs this way though
            self.is_lp_token = "lp token" in self.name.lower()
        else:
            pair_info = dex_info["pair"]
            tokn_info = dex_info["token"]

            self.is_lp_token = self._is_pair(pair_info, tokn_info)

            if self.is_lp_token:
                self.lp_token_0 = HarmonyToken.get_harmony_token_by_address(
                    pair_info["token0"]["id"]
                )
                self.lp_token_1 = HarmonyToken.get_harmony_token_by_address(
                    pair_info["token1"]["id"]
                )

    @staticmethod
    def _is_pair(pair_info: Dict, token_info: Dict) -> bool:
        if bool(pair_info) ^ bool(token_info):
            # if there is only 1 result given the address
            return bool(pair_info)

        # we got an answer back for both a token and an LP pair at the same address
        # this is rare but can happen
        token_trade_vol_usd = token_info["tradeVolumeUSD"]
        token_tx_count = token_info["txCount"]
        token_total_liquidity = token_info["totalLiquidity"]
        if (
            token_trade_vol_usd < 1
            and token_total_liquidity < 10
            and token_tx_count < 100
        ):
            # somewhat hacky solution but check if the single token has unusually
            # low activity. Someone may have created this by mistake, in which
            # case we should prefer the pair's info
            return True

        # this looks more like a token than an LP position
        # haven't seen this happen yet
        return False  # pragma: no cover

    def get_value_from_wei(self, amount: int) -> Decimal:
        return HarmonyAPI.get_value_from_wei(amount, self.decimals)

    @property
    def universal_symbol(self) -> str:
        # many harmony tokens start with a "1", e.g. 1USDC, 1ETH, 1BTC, 1USDT
        return self.symbol[1:] if self.symbol.startswith("1") else self.symbol

    @classmethod
    def get_harmony_token_by_address(
        cls,
        address: Union[HarmonyAddress, str],
        merge_one_wone_names: Optional[bool] = True,
    ) -> HarmonyToken:
        addr_obj = HarmonyAddress.get_harmony_address(address)

        if not HarmonyAPI.address_belongs_to_erc_20_token(addr_obj.eth):
            raise ValueError(
                f"This address does not appear to belong to an ERC/HRC20 token. "
                f"Got address: {address} (type = {type(address)})"
            )

        return HarmonyToken._TOKEN_DIRECTORY.get(addr_obj) or HarmonyToken(
            addr_obj,
            merge_one_wone_names,
        )

    def __str__(self) -> str:  # pragma: no cover
        return "HarmonyToken: {0} ({1}) [{2}] is_lp_token={3}".format(
            self.symbol, self.name, self.address.eth, self.is_lp_token
        )

    def __repr__(self) -> str:  # pragma: no cover
        return super().__repr__() + f" ({self.__str__()})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, HarmonyToken) and self.address == other.address

    def __hash__(self) -> int:
        return hash("harmony_token" + str(self.address.__hash__()))


class HarmonyPlaceholderToken(Token):
    def __init__(
        self,
        wrapped_token: HarmonyToken,
        placeholder_name: str,
        placeholder_symbol: str,
        address: str,
    ) -> None:
        # address need not be real address
        super().__init__(address)

        self._wrapped_token = wrapped_token
        self.name = placeholder_name
        self.symbol = placeholder_symbol

    @property
    def universal_symbol(self) -> str:
        return self.symbol

    @classmethod
    def get_native_token(cls) -> Token:
        return HarmonyToken.get_native_token()

    @property
    def is_native_token(self) -> bool:
        return self._wrapped_token.is_native_token
