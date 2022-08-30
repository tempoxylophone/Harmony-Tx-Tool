from __future__ import annotations
from typing import Dict, Union, Tuple, Any, List
from functools import lru_cache

from web3.contract import ContractFunction
from web3.logs import DISCARD
from web3.types import HexStr
from txtool.utils import get_local_abi

from .api import HarmonyAPI
from .address import HarmonyAddress

T_DECODED_ETH_SIG = Tuple[ContractFunction, Dict[str, Any]]


class HarmonyEVMSmartContract:
    # test each ABI until you reach the end or find a match for decoding
    POSSIBLE_ABIS = [
        "ERC20",
        "ERC721",
        "UniswapV2Router02",
        "UniswapV2Factory",
        "UniswapV2Pair",
        "USDCoin",
        "WrappedONE",
        "TranquilComptroller",
    ]

    @classmethod
    @lru_cache(maxsize=256)
    def lookup_harmony_smart_contract_by_address(
        cls, address: Union[str, HarmonyAddress]
    ) -> HarmonyEVMSmartContract:
        return HarmonyEVMSmartContract(HarmonyAddress.get_harmony_address(address))

    def __init__(self, address: HarmonyAddress):
        self.address: HarmonyAddress = address

        # contract function requires us to know interface of source
        self.has_code = HarmonyAPI.address_belongs_to_smart_contract(self.address.eth)
        self.abi_attempt_idx = 0

        if network_abi := HarmonyAPI.get_abi(self.address.eth):
            # see if you can pull the API from the internet
            self.abi = network_abi
        else:
            # otherwise, default to some well known ABIs that are used
            # frequently with forks of popular protocols
            self.abi = get_local_abi(self.POSSIBLE_ABIS[0])
            self.abi_attempt_idx += 1

        # create contract object
        self.contract = HarmonyAPI.get_contract(self.address.eth, self.abi)

    def get_tx_logs_by_event_name(self, tx_hash: str, event_name: str) -> List[Dict]:
        tx_receipt = HarmonyAPI.get_tx_receipt(tx_hash)
        f = getattr(self.contract.events, event_name)
        return [dict(x) for x in f().processReceipt(tx_receipt, errors=DISCARD)]

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
            self.contract = HarmonyAPI.get_contract(self.address.eth, self.abi)
            self.abi_attempt_idx += 1
            return self.decode_input(tx_input)

    def __str__(self) -> str:  # pragma: no cover
        return f"Harmony Smart Contract at Address: {self.address}"
