from __future__ import annotations
from typing import List, Dict, Optional, Tuple, Iterable, Union
from decimal import Decimal, localcontext
from functools import lru_cache

import requests
from requests.exceptions import JSONDecodeError

from hexbytes import HexBytes
from web3.contract import Contract
from web3.logs import DISCARD
from web3.types import EventData
from web3.exceptions import BadFunctionCallOutput, TransactionNotFound, BlockNotFound

from web3 import Web3
from web3.types import TxReceipt, HexStr

from pyhmy.rpc.exceptions import RPCError, RequestsError, RequestsTimeoutError
from pyhmy import account

from txtool.utils import MAIN_LOGGER, api_retry, get_local_abi


class HarmonyAPI:  # pylint: disable=R0904
    _TIMEOUT = 300  # 5 minutes
    _CUSTOM_EXCEPTIONS: List = [
        RPCError,
        RequestsError,
        RequestsTimeoutError,
    ]
    _NET_HMY_MAIN = "https://a.api.s0.t.hmny.io/"
    _NET_HMY_WEB3 = "https://a.api.s0.t.hmny.io/"

    _w3 = Web3(Web3.HTTPProvider(_NET_HMY_WEB3))
    _ERC20_ABI = get_local_abi("ERC20")
    _ERC721_ABI = get_local_abi("ERC721")

    _JEWEL_CONTRACT = _w3.eth.contract(  # noqa
        address="0x72Cb10C6bfA5624dD07Ef608027E366bd690048F",  # type: ignore
        abi=get_local_abi("JewelToken"),
    )
    _NFT_CONTRACT = _w3.eth.contract(
        address="0xcDFFD2d1CE72aA4140eb3345941CE8D26e38c464",  # type: ignore
        abi=_ERC721_ABI,
    )

    API_NOT_FOUND_MESSAGES = {"Not found", "contract not found"}
    ABI_API_ENDPOINT = (
        "https://ctrver.t.hmny.io/fetchContractCode?contractAddress={0}&shard=0"
    )
    INCORRECT_CONTRACT_ABI_ADDRESSES = (
        # Tranquil Finance 'Comproller' Contract has
        # "ComptrollerErrorReporter" source code linked to
        # its address in the Harmony Explorer
        "0x6a82A17B48EF6be278BBC56138F35d04594587E3",
    )

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_transaction(cls, tx_hash: HexStr) -> Dict:
        return dict(cls._w3.eth.get_transaction(tx_hash))

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_timestamp(cls, block: int) -> int:
        if block < 1:
            raise ValueError("Invalid block... must be at least 1")

        try:
            return cls._w3.eth.get_block(block)["timestamp"]
        except BlockNotFound as err:
            raise ValueError(
                "Got invalid block {0} {1} - this block may not exist yet.".format(
                    block, str(err)
                )
            ) from err

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_tx_receipt(cls, tx_hash: HexStr) -> TxReceipt:
        try:
            return cls._w3.eth.get_transaction_receipt(tx_hash)
        except TransactionNotFound as err:
            raise ValueError(
                "Can't find transaction with hash: {0} ."
                "Invalid transaction {0} {1}".format(tx_hash, str(err))
            ) from err

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_tx_transfer_logs(cls, tx_receipt: TxReceipt) -> Iterable[EventData]:
        events: Iterable[
            EventData
        ] = cls._JEWEL_CONTRACT.events.Transfer().processReceipt(
            tx_receipt, errors=DISCARD
        )
        return events

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_tx_transfer_logs_nft(cls, tx_receipt: TxReceipt) -> Iterable[EventData]:
        events: Iterable[
            EventData
        ] = cls._NFT_CONTRACT.events.Transfer().processReceipt(
            tx_receipt, errors=DISCARD
        )
        return events

    @classmethod
    @lru_cache(maxsize=256)
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_token_info(cls, token_eth_address: str) -> Tuple[str, int, str]:
        contract = cls._w3.eth.contract(  # noqa
            address=Web3.toChecksumAddress(token_eth_address), abi=cls._ERC20_ABI
        )
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        name = contract.functions.name().call()
        return symbol, decimals, name

    @classmethod
    @lru_cache(maxsize=256)
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_nft_info(cls, nft_eth_address: str) -> Tuple[str, int, int]:
        contract = cls._w3.eth.contract(  # noqa
            address=Web3.toChecksumAddress(nft_eth_address), abi=cls._ERC721_ABI
        )
        symbol = contract.functions.symbol().call()
        name = contract.functions.name().call()
        total_supply = contract.functions.totalSupply().call()
        return symbol, name, total_supply

    @staticmethod
    def has_token_info(eth_address: str) -> bool:
        try:
            symbol, decimals, name = HarmonyAPI.get_token_info(eth_address)
            # items with 0 decimals are 1 of 1
            return bool(symbol and name) and decimals >= 0
        except BadFunctionCallOutput:
            return False

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_smart_contract_byte_code(cls, eth_address: str) -> HexBytes:
        return cls._w3.eth.get_code(eth_address)

    @classmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def _get_code(cls, address: str) -> Dict:
        url = cls._get_code_request_url(address)
        r: Dict = requests.get(url, timeout=cls._TIMEOUT).json()
        return r

    @classmethod
    def get_code(cls, address: str) -> Dict:
        try:
            return cls._get_code(address)
        except JSONDecodeError:  # pragma: no cover
            # 502 bad gateway
            return {}

    @classmethod
    @lru_cache(maxsize=256)
    def get_abi(cls, address: str) -> Union[Dict, None]:
        if address in cls.INCORRECT_CONTRACT_ABI_ADDRESSES:
            # hacky handler for incorrect ABIs uploaded to Harmony API
            return None
        source_code = cls.get_code(address)
        return source_code.get("abi")

    @classmethod
    def _get_code_request_url(cls, address: str) -> str:
        return cls.ABI_API_ENDPOINT.format(address)

    @staticmethod
    @lru_cache(maxsize=256)
    def address_belongs_to_smart_contract(eth_address: str) -> bool:
        # null byte if address belongs to a wallet
        # this will return True if this is the address of ERC20 token
        return bool(HarmonyAPI.get_smart_contract_byte_code(eth_address))

    @staticmethod
    @lru_cache(maxsize=256)
    def address_belongs_to_erc_20_token(eth_address: str) -> bool:
        return HarmonyAPI.address_belongs_to_smart_contract(
            eth_address
        ) and HarmonyAPI.has_token_info(eth_address)

    @staticmethod
    def get_harmony_tx_list(
        eth_address: str, dt_ts_lb: int, dt_ts_ub: int, page_size: int = 1_000
    ) -> List[HexStr]:
        # this could be more efficient by estimating the page range for transactions
        txs = []
        num_pages = HarmonyAPI.get_num_tx_for_wallet(eth_address) // page_size + 1

        has_more = True
        p_idx = 0

        while has_more and p_idx < num_pages:
            results = HarmonyAPI._get_tx_page(eth_address, p_idx, page_size)

            in_bounds_txs = [
                x["hash"] for x in results if dt_ts_lb <= x["timestamp"] <= dt_ts_ub
            ]
            txs += in_bounds_txs

            MAIN_LOGGER.info(
                "got page %s/%s of all wallet transactions. Total tx = %s...",
                p_idx + 1,
                num_pages,
                len(txs),
            )

            # the last tx on current page is in time bounds
            has_more = bool(results) and not (
                # request upper bound is greater than returned lower bound
                results[0]["timestamp"]
                < dt_ts_lb
            )
            p_idx += 1

        # de-dupe tx hashes in order, sometimes API returns duplicates in pagination
        MAIN_LOGGER.info("Done fetching transactions from API.")
        return list(dict.fromkeys(txs))

    @staticmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def _get_tx_page(
        eth_address: str, page_num: int, page_size: int, order: Optional[str] = "DESC"
    ) -> List[Dict]:
        # order can be: "DESC" or "ASC"
        # docs: https://api.hmny.io/#:~:text=POSThmyv2_getTransactionsHistory
        return (
            account.get_transaction_history(
                eth_address,
                page=page_num,
                page_size=page_size,
                include_full_tx=True,
                endpoint=HarmonyAPI._NET_HMY_MAIN,
                order=order,
            )
            or []
        )

    @staticmethod
    @api_retry(custom_exceptions=_CUSTOM_EXCEPTIONS)
    def get_num_tx_for_wallet(eth_address: str) -> int:
        return int(
            account.get_transaction_count(
                eth_address, "latest", endpoint=HarmonyAPI._NET_HMY_MAIN
            )
        )

    @classmethod
    def get_contract(cls, address: str, abi: Dict) -> Contract:
        return cls._w3.eth.contract(Web3.toChecksumAddress(address), abi=abi)

    @classmethod
    def is_eth_address(cls, address: str) -> bool:
        return cls._w3.isAddress(address)

    @staticmethod
    def clean_eth_address_str(eth_address_str: str) -> str:
        return Web3.toChecksumAddress(eth_address_str)

    @staticmethod
    def get_value_from_wei(amount: int, num_decimals: int) -> Decimal:
        # from web3.from_wei function
        with localcontext() as ctx:
            ctx.prec = 999

            # do conversion
            num = Decimal(value=amount, context=ctx)
            val = num / Decimal("1" + "".join("0" for _ in range(num_decimals)))
        return val

    @staticmethod
    def get_coin_amount_from_tx_data(result: Dict) -> Decimal:
        return Decimal(Web3.fromWei(result["value"], "ether"))

    @staticmethod
    def get_tx_fee_from_tx_data(result: Dict) -> Decimal:
        tx_receipt = HarmonyAPI.get_tx_receipt(result["hash"])
        return Web3.fromWei(result["gasPrice"], "ether") * Decimal(
            tx_receipt["gasUsed"]
        )
