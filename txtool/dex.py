from typing import Iterable, Dict, List, Tuple, Union, Optional
from decimal import Decimal

import requests


class UniswapV2ForkGraph:
    _UNIX_TS_1_DAY_APPROX = 86400

    def __init__(
        self,
        subgraph_url: str,
        authority: Optional[str] = "",
        origin: Optional[str] = "",
    ):
        self.subgraph_url = subgraph_url
        self.authority = authority
        self.origin = origin

    def _graph_ql_request(self, payload: Dict[str, str]) -> Dict:
        r = requests.post(
            self.subgraph_url, headers=self._get_graph_ql_headers(), json=payload
        ).json()

        try:
            return r["data"]
        except KeyError as e:
            raise RuntimeError(
                f"Could not get data for subgraph from URL: {self.subgraph_url} "
                f"with payload: {payload}. Got response: {r}"
            ) from e

    def _get_graph_ql_headers(self) -> Dict[str, str]:
        return {
            "authority": str(self.authority),
            "pragma": "no-cache",
            "cache-control": "no-cache",
            "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="99", "Google Chrome";v="99"',
            "accept": "*/*",
            "dnt": "1",
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.81 Safari/537.38",
            "sec-ch-ua-platform": '"macOS"',
            "origin": str(self.origin),
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": str(self.origin),
            "accept-language": "en-US,en;q=0.9",
        }

    @classmethod
    def _q_get_graph_ql_token_or_pair_info(cls, token_or_pair_address: str):
        query = """
        query coininfo($token_address: ID!)  {
            pair(id: $token_address) {
                id
                __typename
                token0 {
                  id
                  __typename
                  symbol
                  name
                  decimals
                  totalSupply
                  tradeVolumeUSD
                  txCount
                  totalLiquidity
                  derivedETH
                }
                token1 {
                  id
                  __typename
                  symbol
                  name
                  decimals
                  totalSupply
                  tradeVolumeUSD
                  txCount
                  totalLiquidity
                  derivedETH
                }
            }
            token(id: $token_address) {
                id
                __typename
                symbol
                name
                decimals
                totalSupply
                tradeVolumeUSD
                txCount
                totalLiquidity
                derivedETH
            }
        }
        """
        return {
            "operationName": "coininfo",
            "variables": {
                "token_address": token_or_pair_address.lower()
            },  # case sensitive
            "query": query,
        }

    def get_token_or_pair_info(self, token_or_pair_address: str) -> Dict:
        data = self._graph_ql_request(
            self._q_get_graph_ql_token_or_pair_info(token_or_pair_address)
        )

        # cast fields from strings
        data["token"] = self._cast_token_object(data["token"])

        if data["pair"]:
            data["pair"]["token0"] = self._cast_token_object(data["pair"]["token0"])
            data["pair"]["token1"] = self._cast_token_object(data["pair"]["token1"])

        return data

    @staticmethod
    def _cast_token_object(token_object: Union[Dict, None]) -> Union[Dict, None]:
        # mutate token object
        if token_object is None:
            return token_object

        formats = (
            ("decimals", int),
            ("derivedETH", Decimal),
            ("totalLiquidity", Decimal),
            ("totalSupply", Decimal),
            ("tradeVolumeUSD", Decimal),
            ("txCount", int),
        )
        for f in formats:
            s, o = f
            token_object[s] = o(token_object[s])

        return token_object

    @classmethod
    def _q_get_graph_ql_token_price_block(cls, block_num: int) -> str:
        """
        Note on bundle: https://docs.uniswap.org/protocol/V2/reference/API/entities#bundle

        "The Bundle is used as a global store of derived ETH price in USD" - Uniswap Docs
        """
        return f"""
        t{block_num}: 
            token(id: $token_id, block: {{number: {block_num}}}) {{
              __typename
              derivedETH
            }}
        b{block_num}:
            bundle(id: "1", block: {{number: {block_num}}}) {{
              ethPrice
              __typename
            }}
        """

    @classmethod
    def _q_get_graph_ql_price_payload(
        cls, token_address: str, block_nums: Iterable[int]
    ) -> Dict:
        """
        More info here: https://docs.uniswap.org/protocol/V2/reference/API/queries
        """
        query = "query blocks($token_id: ID!) {{{0}}}".format(
            "".join((cls._q_get_graph_ql_token_price_block(y) for y in block_nums))
        )
        return {
            "operationName": "blocks",
            "variables": {"token_id": token_address.lower()},  # case sensitive
            "query": query,
        }

    @classmethod
    def _q_get_graph_ql_lp_pair_payload(
        cls, lp_pair_address: str, tx_start_ts: int, tx_end_ts: int
    ) -> Dict:
        ts_min, ts_max = cls._compute_ts_bounds(tx_start_ts, tx_end_ts)
        query = """
        query pairs($lp_pair_id: ID!, $ts_min: Int!, $ts_max: Int!) {
          pair(id: $lp_pair_id) {
            id
            liquidityPositionSnapshots(orderBy: timestamp, where: {timestamp_gte: $ts_min, timestamp_lte: $ts_max}) {
              timestamp
              block
              reserve0
              reserve1
              token0PriceUSD
              token1PriceUSD
              reserveUSD
              liquidityTokenTotalSupply
            }
            token0 {
            id
            symbol
            name
            __typename
          }
            token1 {
            id
            symbol
            name
            __typename
          }
            __typename
          }
        }
        """
        return {
            "operationName": "pairs",
            "variables": {
                "lp_pair_id": lp_pair_address.lower(),  # case sensitive
                # snapshot not guaranteed at every time, need to approximate
                "ts_min": ts_min,
                "ts_max": ts_max,
            },
            "query": query,
        }

    def _get_graph_ql_pair_data(
        self, lp_pair_address: str, tx_start_ts: int, tx_end_ts: int
    ) -> Dict[str, Dict]:
        if tx_start_ts > tx_end_ts:
            raise ValueError(
                "Invalid timestamp range for liquidity position price query! "
                "Date: ({0}, {1})".format(tx_start_ts, tx_end_ts)
            )

        return self._graph_ql_request(
            self._q_get_graph_ql_lp_pair_payload(
                lp_pair_address, tx_start_ts, tx_end_ts
            )
        )

    @staticmethod
    def _compute_ts_bounds(ts_min, ts_max):
        return (
            ts_min - UniswapV2ForkGraph._UNIX_TS_1_DAY_APPROX,
            ts_max + UniswapV2ForkGraph._UNIX_TS_1_DAY_APPROX,
        )

    def _get_graph_ql_price_query_data(
        self, token_address: str, block_nums: Iterable[int]
    ) -> Dict[str, Dict]:
        return self._graph_ql_request(
            self._q_get_graph_ql_price_payload(token_address, block_nums)
        )

    @classmethod
    def _graph_ql_price_result_to_block_price_timeseries(
        cls, block_nums: Iterable[int], price_query_data: Dict
    ) -> Tuple[Dict[int, Decimal], bool]:
        ts = {}
        all_zero = True
        for block_num in block_nums:
            # NB: "ethPrice" is actually price of harmony ONE, not eth
            eth_price = Decimal(price_query_data["b" + str(block_num)]["ethPrice"])
            token_eth = Decimal(
                # could be null if DEX returned nothing for this token
                (price_query_data["t" + str(block_num)] or {}).get("derivedETH", 0)
            )
            ts[block_num] = eth_price * token_eth
            all_zero = all_zero and ts[block_num] == 0

        return ts, all_zero

    def get_token_price_by_block_timeseries(
        self, token_address: str, block_nums: Iterable[int]
    ) -> Tuple[Dict[int, Decimal], bool]:
        return self._graph_ql_price_result_to_block_price_timeseries(
            block_nums, self._get_graph_ql_price_query_data(token_address, block_nums)
        )

    def get_lp_token_price_by_block_timeseries(
        self, lp_token_address: str, min_ts: int, max_ts: int, block_nums: Iterable[int]
    ) -> Dict[int, Decimal]:
        price_query_data = self._get_graph_ql_pair_data(
            lp_token_address, min_ts, max_ts
        )
        price_blocks: List[Dict] = price_query_data["pair"][
            "liquidityPositionSnapshots"
        ]
        ts = {}

        for block_num in block_nums:
            price_block = price_blocks[
                self._get_best_block_idx(block_num, price_blocks)
            ]

            # token value = (total value of pool) / (total supply of pool)
            # source: https://dailydefi.org/articles/lp-token-value-calculation/
            pool_supply = Decimal(price_block["liquidityTokenTotalSupply"])
            pool_value = Decimal(price_block["reserveUSD"])

            ts[block_num] = pool_value / pool_supply

        return ts

    @staticmethod  # noqa: E741
    def _get_best_block_idx(find_block: int, price_blocks: List[Dict]) -> int:
        # binary search for correct block (kind of), blocks are in order of timestamp ASC
        l, u = 0, len(price_blocks) - 1
        best_block_info = (0, float("inf"))
        while l <= u:  # noqa
            c = (u + l) // 2
            curr_block = price_blocks[c]["block"]

            # take note of closest block encountered so far
            error = abs(curr_block - find_block)
            best_block_info = (
                (c, error) if error < best_block_info[1] else best_block_info
            )

            if find_block < curr_block:
                u = c - 1
            elif find_block > curr_block:
                l = c + 1  # noqa
            else:
                # found exact match (unlikely but possible)
                return c

        # return the index of the best choice given the block number
        return best_block_info[0]

    def __str__(self) -> str:
        return "DEX Graph at URL: " + self.subgraph_url
