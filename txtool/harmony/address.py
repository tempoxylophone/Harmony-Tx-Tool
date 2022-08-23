from __future__ import annotations

from typing import Dict, Union

from txtool import pyhmy
from txtool.utils import MAIN_LOGGER
from .api import HarmonyAPI
from .abc import Token


class BadAddressException(Exception):
    pass


class HarmonyAddress:
    FORMAT_ETH = "eth"
    FORMAT_ONE = "one"
    _HARMONY_BECH32_HRP = "one"
    _ADDRESS_DIRECTORY: Dict[str, HarmonyAddress] = {}

    def __init__(self, eth_address: str):
        self.addresses = {
            self.FORMAT_ETH: "",
            self.FORMAT_ONE: "",
        }

        if self.is_valid_eth_address(eth_address):
            # given an ethereum address
            self.address_format = self.FORMAT_ETH
            self.addresses[self.FORMAT_ETH] = eth_address
            self.addresses[self.FORMAT_ONE] = self.convert_hex_to_one(eth_address)
        elif self.is_valid_one_address(eth_address):
            raise BadAddressException(
                "Use ETH address, not ONE address! Got: {0}".format(eth_address)
            )
        else:
            raise BadAddressException("Bad address! Got: {0}".format(eth_address))

        MAIN_LOGGER.info(
            "Encountered new address: %s. Address book now contains: %s addresses",
            eth_address,
            len(HarmonyAddress._ADDRESS_DIRECTORY),
        )

        # add to directory
        HarmonyAddress._ADDRESS_DIRECTORY[self.eth] = self

        self.belongs_to_smart_contract = HarmonyAPI.address_belongs_to_smart_contract(
            self.eth
        )

        # this will be set if the address is called in the constructor of token
        self.belongs_to_token = (
            self.belongs_to_smart_contract
            and HarmonyAPI.address_belongs_to_erc_20_token(self.eth)
        )

        self.token: Union[Token, None] = None

    @classmethod
    def clear_directory(cls) -> None:
        cls._ADDRESS_DIRECTORY = {}

    def get_address_str(self, address_format: str) -> str:
        return self.addresses[address_format]

    def get_eth_address(self) -> str:
        return self.get_address_str(self.FORMAT_ETH)

    def get_one_address(self) -> str:
        return self.get_address_str(self.FORMAT_ONE)

    @property
    def eth(self) -> str:
        return self.get_eth_address()

    @property
    def one(self) -> str:
        return self.get_one_address()

    @property
    def belongs_to_non_token_smart_contract(self) -> bool:
        return self.belongs_to_smart_contract and not self.belongs_to_token

    @classmethod
    def get_address_string_format(cls, address_string: str) -> str:
        if cls.is_valid_one_address(address_string):
            return cls.FORMAT_ONE
        if cls.is_valid_eth_address(address_string):
            return cls.FORMAT_ETH
        raise BadAddressException(
            "get_address_string_format(): Bad address, neither eth or one! Got: {0}".format(
                address_string
            )
        )

    @classmethod
    def address_str_is_eth(cls, address_str: str) -> bool:
        # also checks if address is neither one or eth, throws ValueError in that case
        return cls.get_address_string_format(address_str) == cls.FORMAT_ETH

    @classmethod
    def get_harmony_address_by_string(cls, address_str: str) -> HarmonyAddress:
        eth_address = (
            address_str
            if cls.address_str_is_eth(address_str)
            else cls.convert_one_to_hex(address_str)
        )

        # if given a lowercase address, clean it
        eth_address = cls.clean_eth_address_str(eth_address)

        # eth address is always the key
        return HarmonyAddress._ADDRESS_DIRECTORY.get(eth_address) or HarmonyAddress(
            eth_address
        )

    @classmethod
    def get_harmony_address(
        cls,
        address_object: Union[str, HarmonyAddress],
    ) -> HarmonyAddress:
        return (
            address_object
            if isinstance(address_object, HarmonyAddress)
            else (cls.get_harmony_address_by_string(address_object))
        )

    @classmethod
    def convert_one_to_hex(cls, one_string_hash: str) -> str:
        return str(pyhmy.util.convert_one_to_hex(one_string_hash))

    @classmethod
    def convert_hex_to_one(cls, eth_string_hash: str) -> str:
        return str(pyhmy.util.convert_hex_to_one(eth_string_hash))

    @classmethod
    def is_valid_one_address(cls, address: str) -> bool:
        if not address:
            # empty or null
            return False
        return pyhmy.account.is_valid_address(address)

    @classmethod
    def is_valid_eth_address(cls, address: str) -> bool:
        if not address:
            # empty or null
            return False
        return HarmonyAPI.is_eth_address(address)

    @staticmethod
    def clean_eth_address_str(eth_address_str: str) -> str:
        return HarmonyAPI.clean_eth_address_str(eth_address_str)

    def __str__(self) -> str:
        # default to eth address format
        return self.get_eth_address()

    def __eq__(self, other: object) -> bool:
        return isinstance(other, HarmonyAddress) and (
            self.eth == other.eth and self.one == other.one
        )

    def __hash__(self) -> int:
        return hash(self.eth)
