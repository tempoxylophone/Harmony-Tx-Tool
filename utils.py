from pyharmony import pyharmony

HARMONY_BECH32_HRP = "one"


def convert_one_to_hex(one_string_hash) -> str:
    return pyharmony.util.convert_one_to_hex(one_string_hash)


def convert_hex_to_one(eth_string_hash) -> str:
    p = bytearray.fromhex(
        # remove 0x prefix from ethereum hash if necessary
        eth_string_hash[2:] if eth_string_hash.startswith("0x") else eth_string_hash
    )

    # encode to bech32 style hash "one" hash
    return pyharmony.bech32.bech32_encode(
        HARMONY_BECH32_HRP,
        pyharmony.bech32.convertbits(p, 8, 5)
    )
