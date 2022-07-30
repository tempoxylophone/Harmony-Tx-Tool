from __future__ import annotations
from typing import Dict, Union, Tuple, Any
from functools import lru_cache
from web3.contract import ContractFunction
from web3.types import HexStr
from txtool.utils import get_local_abi

from .api import HarmonyAPI

T_DECODED_ETH_SIG = Tuple[ContractFunction, Dict[str, Any]]


class HarmonyEVMSmartContract:
    POSSIBLE_ABIS = ["ERC20", "ERC721", "UniswapV2Router02", "USD Coin", "Wrapped ONE"]

    @classmethod
    @lru_cache(maxsize=256)
    def lookup_harmony_smart_contract_by_address(
        cls, address: str, name: str = ""
    ) -> HarmonyEVMSmartContract:
        return HarmonyEVMSmartContract(address, name)

    def __init__(self, address: str, assigned_name: str):
        self.address = address
        self.name = assigned_name

        # contract function requires us to know interface of source
        self.code = HarmonyAPI.get_code(address)
        self.has_code = not self._is_missing(self.code)
        self.abi = (
            self.code["abi"] if self.has_code else get_local_abi(self.POSSIBLE_ABIS[0])
        )
        self.abi_attempt_idx = 1
        self.contract = HarmonyAPI.get_contract(self.address, self.abi)

    def decode_input(
        self, tx_input: HexStr
    ) -> Tuple[bool, Union[T_DECODED_ETH_SIG, None]]:
        if self.abi_attempt_idx > len(self.POSSIBLE_ABIS) - 1:
            # can't decode this, even after trying a few generic ABIs
            return False, None

        try:
            f = self.contract.decode_function_input(tx_input)
            return True, f
        except ValueError:
            # can't decode this input, keep shuffling different ABIs until get match, then stop
            self.abi = get_local_abi(self.POSSIBLE_ABIS[self.abi_attempt_idx])
            self.abi_attempt_idx += 1
            return self.decode_input(tx_input)

    @staticmethod
    def _is_missing(code: Dict) -> bool:
        return code.get("message") in HarmonyAPI.API_NOT_FOUND_MESSAGES
