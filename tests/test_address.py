from txtool.harmony import HarmonyAddress


def test_convert_one_to_hex():
    assert HarmonyAddress.convert_one_to_hex(
        '0xebcd16e8c1d8f493ba04e99a56474122d81a9c58') == '0xeBCD16e8c1D8f493bA04E99a56474122D81A9c58'
    assert HarmonyAddress.convert_one_to_hex(
        'one1a0x3d6xpmr6f8wsyaxd9v36pytvp48zckswvv9') == '0xeBCD16e8c1D8f493bA04E99a56474122D81A9c58'


def test_convert_hex_to_one():
    assert HarmonyAddress.convert_hex_to_one(
        '0xebcd16e8c1d8f493ba04e99a56474122d81a9c58') == 'one1a0x3d6xpmr6f8wsyaxd9v36pytvp48zckswvv9'
    assert HarmonyAddress.convert_hex_to_one(
        'one1a0x3d6xpmr6f8wsyaxd9v36pytvp48zckswvv9') == 'one1a0x3d6xpmr6f8wsyaxd9v36pytvp48zckswvv9'
