from .dex import UniswapDexEditor, MasterChefDexEditor


class DefiKingdomsLiquidityEditor(UniswapDexEditor):
    CONTRACT_ADDRESSES = [
        # Defi Kingdoms Uniswap Router v2 Contract
        "0x24ad62502d1C652Cc7684081169D04896aC20f30",
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)


class DefiKingdomsClaimsEditor(MasterChefDexEditor):
    GOV_TOKEN_SYMBOL = "JEWEL"
    LP_TOKEN_SYMBOL_PREFIX = "JEWEL-LP"
    CONTRACT_ADDRESSES = [
        # Defi Kingdoms Gardener Contract
        "0xDB30643c71aC9e2122cA0341ED77d09D5f99F924"
    ]

    def __init__(self) -> None:
        super().__init__(self.CONTRACT_ADDRESSES)
