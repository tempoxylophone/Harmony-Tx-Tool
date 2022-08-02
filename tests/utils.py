from typing import List, Dict, Union, Callable
import pathlib
import json
import vcr

from txtool.harmony import DexPriceManager
from txtool.transactions import WalletActivity
from txtool.koinly import is_cost


def get_non_cost_transactions_from_txt_hash(
        wallet_address: str, tx_hash: str
) -> List[WalletActivity]:
    non_cost_txs = [
        x
        for x in WalletActivity.extract_all_wallet_activity_from_transaction(
            wallet_address, tx_hash
        )
        if not is_cost(x)
    ]

    # side effect
    DexPriceManager.initialize_static_price_manager(non_cost_txs)

    return non_cost_txs


class NestedBytesSerializer:
    """
    Based on: https://github.com/kevin1024/vcrpy/blob/master/vcr/serializers/jsonserializer.py
    """
    ENCODING = "ISO-8859-1"
    BYTES_DELIMITER = "bytes_"

    def serialize(self, cassette_dict: Dict) -> str:
        # encode bytes in response body
        self._cast(
            cassette_dict,
            lambda x: isinstance(x, bytes),
            lambda x: self.BYTES_DELIMITER + x.decode(encoding=self.ENCODING)
        )

        # dump to string
        return json.dumps(cassette_dict, indent=4) + "\n"

    def _cast(self, json_body: Union[List, Dict, str], cond: Callable, operation: Callable) -> None:
        # mutate dictionary object by reference
        if isinstance(json_body, list):
            [self._cast(x, cond, operation) for x in json_body]
        elif isinstance(json_body, dict):
            for k, v in json_body.items():
                if cond(v):
                    json_body[k] = operation(v)
                else:
                    self._cast(v, cond, operation)

    def deserialize(self, cassette_string: str) -> Dict:
        cassette_dict = json.loads(cassette_string)

        # decode bytes in response body
        self._cast(
            cassette_dict,
            lambda x: isinstance(x, str) and x.startswith(self.BYTES_DELIMITER),
            lambda x: bytes(x[len(self.BYTES_DELIMITER):], encoding=self.ENCODING)
        )

        # return as dictionary object
        return cassette_dict


def remove_set_cookie() -> Callable:
    def before_record_response(response) -> Dict:
        response['headers']['Set-Cookie'] = []
        return response

    return before_record_response


def get_vcr(
        file_obj,
) -> vcr.VCR:
    fixture_path = f'{pathlib.Path(file_obj).parent.absolute()}/fixtures'

    # return vcr object with configuration
    v = vcr.VCR(cassette_library_dir=fixture_path)
    v.register_serializer('bytes', NestedBytesSerializer())
    v.serializer = "bytes"
    v.filter_headers = ["Cookie"]
    v.before_record_response = remove_set_cookie()
    return v
