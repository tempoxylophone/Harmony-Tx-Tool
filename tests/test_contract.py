import pytest  # noqa

from txtool.harmony import HarmonyEVMSmartContract
from .utils import get_vcr

vcr = get_vcr(__file__)


@vcr.use_cassette()
def test_get_redeem_logs_using_smart_contract() -> None:
    tranq_contract = "0x34B9aa82D89AE04f0f546Ca5eC9C93eFE1288940"
    c = HarmonyEVMSmartContract.lookup_harmony_smart_contract_by_address(tranq_contract)
    redeems = c.get_tx_logs_by_event_name(
        # random tx from explorer
        "0xf1855a772a7abae776110b46ab57aea550e96f7251a8ea0d20c0ee7fca5610c3",
        "Redeem",
    )
    assert len(redeems) == 1

    redeem_log = redeems[0]

    # address is HRC20 Tranquil ONE (tqONE)
    assert redeem_log["address"] == "0x34B9aa82D89AE04f0f546Ca5eC9C93eFE1288940"
    assert redeem_log["event"] == "Redeem"

    args = redeem_log["args"]

    # original caller of root tx
    assert args["redeemer"] == "0x83AfD8Cca4eb680fF6c843246Ceece821f52B6c2"

    # ONE you get back
    assert args["redeemAmount"] == 5153849689761429713829
    # tqONE you send
    assert args["redeemTokens"] == 24664261592405
