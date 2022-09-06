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

        symbol, decimals, name = HarmonyAPI.get_token_info(self.address.eth)
        self.name = name
        self._symbol = symbol
        self.decimals = decimals

        # DEX stuff
        self.is_lp_token = False
        self.lp_token_0: Union[HarmonyToken, None] = None
        self.lp_token_1: Union[HarmonyToken, None] = None

        if self._symbol == "WONE":
            # consider WONE and ONE equivalent by symbol
            if merge_one_wone_names:
                self._symbol = NATIVE_TOKEN_SYMBOL
        else:
            # if not a native currency, try to see if it an LP position
            self._set_is_lp_token_guess()

        # add self to directory for later
        HarmonyToken._TOKEN_DIRECTORY[self.address] = self

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

    @classmethod
    def clear_directory(cls) -> None:
        cls._TOKEN_DIRECTORY = {}

    @classmethod
    def get_native_token(cls) -> HarmonyToken:
        return cls.get_harmony_token_by_address(NATIVE_TOKEN_ETH_ADDRESS_STR)

    @classmethod
    def get_native_token_eth_address_str(cls) -> str:
        return NATIVE_TOKEN_ETH_ADDRESS_STR

    @classmethod
    def get_address_and_set_token(cls, eth_address_str: str) -> HarmonyAddress:
        addr_obj = HarmonyAddress.get_harmony_address(eth_address_str)
        try:
            # create token object
            HarmonyToken.get_harmony_token_by_address(addr_obj)
        except ValueError:
            # address does not belong to token
            pass

        return addr_obj

    @property
    def is_native_token(self) -> bool:
        return bool(self.address.eth == NATIVE_TOKEN_ETH_ADDRESS_STR)

    @property
    def universal_symbol(self) -> str:
        if self.is_lp_token:
            return self.symbol

        if self._symbol.startswith("1"):
            # many harmony tokens start with a "1", e.g. 1USDC, 1ETH, 1BTC, 1USDT
            return self._symbol[1:]

        return self._symbol

    @property
    def symbol(self) -> str:
        if self.is_lp_token and self.lp_token_1 and self.lp_token_0:
            # need something to distinguish LP tokens of different address but
            # that have the same name
            return (
                f"{self._symbol} "
                f"({self.lp_token_0.universal_symbol}/{self.lp_token_1.universal_symbol})"
            )

        return self._symbol

    def _set_is_lp_token_guess(self) -> None:
        dex_info = self._VIPERSWAP.get_token_or_pair_info(self.address.eth)

        if not dex_info:
            # cannot get API response - guess based on the name
            # can't retrieve pairs this way though
            self.is_lp_token = "lp token" in self.name.lower()
        else:
            pair_info = dex_info["pair"]
            tokn_info = dex_info["token"]

            if self._is_pair(pair_info, tokn_info):
                self.is_lp_token = True

                # get in alphabetical order by universal symbol
                t0, t1 = sorted(
                    (
                        HarmonyToken.get_harmony_token_by_address(
                            pair_info["token0"]["id"]
                        ),
                        HarmonyToken.get_harmony_token_by_address(
                            pair_info["token1"]["id"]
                        ),
                    ),
                    key=lambda x: x.universal_symbol,
                )
                self.lp_token_0 = t0
                self.lp_token_1 = t1

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

    @property
    def knows_lp_token_pairs(self) -> bool:
        return self.is_lp_token and bool(self.lp_token_0) and bool(self.lp_token_1)

    def get_value_from_wei(self, amount: int) -> Decimal:
        return HarmonyAPI.get_value_from_wei(amount, self.decimals)

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
        self._symbol = placeholder_symbol

    @property
    def universal_symbol(self) -> str:
        return self.symbol

    @classmethod
    def get_native_token(cls) -> Token:
        return HarmonyToken.get_native_token()

    @property
    def is_native_token(self) -> bool:
        return self._wrapped_token.is_native_token


class HarmonyNFTCollection:
    _NFT_COLLECTION_DIRECTORY: Dict[str, HarmonyNFTCollection] = {}

    def __init__(
        self,
        address: Union[str, HarmonyAddress],
    ) -> None:
        # koinly has 5000 unique placeholders for NFTs
        # e.g. NFT1, NFT2, NFT3, ...,
        # each unique NFT has to have its own placeholder.
        # source:
        # https://help.koinly.io/en/articles/5742771-how-to-add-nft-trades-manually-using-placeholders
        self.address = HarmonyAddress.get_harmony_address(address)

        symbol, name, total_supply = HarmonyAPI.get_nft_info(self.address.eth)
        self.symbol = symbol
        self.name = name
        self.total_supply = total_supply

    @classmethod
    def clear_directory(cls) -> None:
        cls._NFT_COLLECTION_DIRECTORY = {}

    @classmethod
    def create_nft_collection(cls, address_eth_str: str) -> HarmonyNFTCollection:
        if address_eth_str in cls._NFT_COLLECTION_DIRECTORY:
            return cls._NFT_COLLECTION_DIRECTORY[address_eth_str]

        return HarmonyNFTCollection(address_eth_str)


class HarmonyNFT(Token):
    # global ID for Koinly
    _GLOBAL_ID_START_AT = 1
    _GLOBAL_ID = _GLOBAL_ID_START_AT
    _NFT_DIRECTORY: Dict[str, HarmonyNFT] = {}

    @property
    def is_native_token(self) -> bool:
        return False

    @classmethod
    def get_native_token(cls) -> HarmonyToken:
        return HarmonyToken.get_native_token()

    @property
    def universal_symbol(self) -> str:
        # do not change anything
        return f"NFT{self.koinly_nft_id}"

    @property
    def full_name(self) -> str:
        return f"{self.collection.name} {self.token_id}/{self.collection.total_supply}"

    def __init__(
        self,
        token_id: int,
        global_id: int,
        collection: HarmonyNFTCollection,
    ) -> None:
        super().__init__(collection.address)

        self.collection = collection
        self.token_id = token_id
        self.koinly_nft_id = global_id
        self._symbol = collection.symbol + " #" + str(self.token_id)
        self.history: Dict[str, Decimal] = {}

    @staticmethod
    def create_nft_lookup_hash(collection_eth_address: str, token_id: int) -> str:
        return f"nft-{collection_eth_address}-{token_id}"

    @classmethod
    def create_nft(cls, token_id: int, collection: HarmonyNFTCollection) -> HarmonyNFT:
        lookup = cls.create_nft_lookup_hash(collection.address.eth, token_id)

        if lookup in cls._NFT_DIRECTORY:
            return cls._NFT_DIRECTORY[lookup]

        nft = HarmonyNFT(token_id, cls._GLOBAL_ID, collection)
        cls._GLOBAL_ID += 1
        return nft

    @classmethod
    def clear_directory(cls) -> None:
        cls._NFT_DIRECTORY = {}
        cls._GLOBAL_ID = cls._GLOBAL_ID_START_AT

    def add_event(self, tx_hash: str, cost_in_one: Decimal) -> None:
        self.history[tx_hash] = cost_in_one

    @property
    def latest_price_in_one(self) -> Decimal:
        if not self.history:
            return Decimal(0)

        # dicts are ordered in python3
        txs = list(self.history)[-1]
        return self.history[txs]

    def __eq__(self, other: object) -> bool:
        return isinstance(other, HarmonyNFT) and (
            other.address == self.address and other.token_id == self.token_id
        )

    def __hash__(self) -> int:
        return hash(self.create_nft_lookup_hash(self.address.eth, self.token_id))
