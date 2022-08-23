from typing import List, Dict, Union, Callable, Iterable
import pathlib
import copy
import json
import vcr  # type: ignore
from vcr.request import Request as VCRMockRequest  # type: ignore

HEADERS_TO_REMOVE = (
    "Cookie",
    "Set-Cookie",
    "ETag",
    "CF-RAY",
    "Alternate-Protocol",
    "Date",
    "X-Request-Id",
    "Expires",
    "X-Runtime",
    "Expect-CT",
)
REQUEST_BODY_PROPERTIES_TO_REMOVE = (
    # For some reason, web3.py adds an "ID" property to the body of a request to a Harmony RPC.
    # This ID can be different for what is otherwise an identical request. To allow matching in
    # vcrpy on the raw body of a request, we should remove it from all bodies before it is persisted.
    "id",
)


class NestedBytesSerializer:
    """
    Based on: https://github.com/kevin1024/vcrpy/blob/master/vcr/serializers/jsonserializer.py
    """

    ENCODING = "ISO-8859-1"
    BYTES_DELIMITER = "bytes_"

    def serialize(self, cassette_dict: Dict) -> str:  # pragma: no cover
        # omitted from coverage because this never runs if all functions that use
        # cassettes already use them

        # encode bytes in response body
        self._cast(
            cassette_dict,
            lambda x: isinstance(x, bytes),
            lambda x: self.BYTES_DELIMITER + x.decode(encoding=self.ENCODING),
        )

        # dump to string
        return json.dumps(cassette_dict, indent=4) + "\n"

    def _cast(
        self, json_body: Union[List, Dict, str], cond: Callable, operation: Callable
    ) -> None:
        # mutate dictionary object by reference
        if isinstance(json_body, list):
            for x in json_body:
                self._cast(x, cond, operation)
        elif isinstance(json_body, dict):
            for k, v in json_body.items():
                if cond(v):
                    json_body[k] = operation(v)
                else:
                    self._cast(v, cond, operation)

    def deserialize(self, cassette_string: str) -> Dict:
        cassette_dict: Dict = json.loads(cassette_string)

        # decode bytes in response body
        self._cast(
            cassette_dict,
            lambda x: isinstance(x, str) and x.startswith(self.BYTES_DELIMITER),
            lambda x: bytes(x[len(self.BYTES_DELIMITER) :], encoding=self.ENCODING),
        )

        # return as dictionary object
        return cassette_dict


def remove_sensitive_responses() -> Callable:
    def before_record_response(response: Dict) -> Dict:
        response_headers = response["headers"]
        for h in HEADERS_TO_REMOVE:
            headers = [x for x in response_headers]
            try:
                # case insensitive replace header with nothing, HTTP headers
                # do need to have consistent case
                idx = [x.lower() for x in headers].index(h.lower())
                response_headers[headers[idx]] = []
            except ValueError:
                # header to remove not contained in response
                pass
        return response

    return before_record_response


def edit_request_body(body_keys_to_remove: Iterable[str]) -> Callable:
    def before_record_request(request: VCRMockRequest) -> VCRMockRequest:
        # see info on copying request here:
        # https://medium.com/@george.shuklin/tips-and-tricks-on-http-s-session-recording-4194f99adbf#:~:text=Do%20not%20mangle%20request
        request = copy.deepcopy(request)

        if r_body := request._body:  # noqa
            decoded = json.loads(r_body.decode("utf-8"))

            # remove keys from the body that may make matching
            # problematic
            for key in body_keys_to_remove:
                if key in decoded:
                    decoded.pop(key)

            encoded = bytes(json.dumps(decoded), "utf-8")

            # set modified body for request object
            request._body = encoded

        return request

    return before_record_request


def get_vcr(
    file_obj: str,
) -> vcr.VCR:
    """
    Called once at the top of any test file that uses request persisting
    """
    fixture_path = f"{pathlib.Path(file_obj).parent.absolute()}/fixtures"

    # return vcr object with configuration
    v = vcr.VCR(cassette_library_dir=fixture_path)

    # serializer to handle nested bytes
    v.register_serializer("bytes", NestedBytesSerializer())
    v.serializer = "bytes"

    v.before_record_request = edit_request_body(REQUEST_BODY_PROPERTIES_TO_REMOVE)
    v.before_record_response = remove_sensitive_responses()

    # ensure to match on raw body, graph QL requests look identical except for
    # the query passed in their json / body property
    v.match_on = ("method", "scheme", "host", "port", "path", "query", "raw_body")
    return v
