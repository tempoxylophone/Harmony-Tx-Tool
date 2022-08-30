from .dex import UniswapDexEditor


class DefiKingdomsLiquidityEditor(UniswapDexEditor):
    CONTRACT_ADDRESSES = [
        # Defi Kingdoms Uniswap Router v2 Contract
        "0x24ad62502d1C652Cc7684081169D04896aC20f30",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)
