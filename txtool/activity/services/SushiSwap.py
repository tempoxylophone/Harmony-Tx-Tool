from .dex import UniswapDexEditor


class SushiSwapLiquidityEditor(UniswapDexEditor):
    CONTRACT_ADDRESSES = [
        # SushiSwap Uniswap Router v2 Contract
        "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)
