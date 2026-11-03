from unittest.mock import patch, MagicMock
import pytest
import requests
from config.settings import Settings
from core.meta_client import MetaClient, MetaAPIError, extract_text

S = Settings(api_key="k", base_url="https://api.meta.ai/v1", model="m")


def resp(status=200, body=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body if body is not None else {}
    r.text = ""
    return r


def test_parses_responses_payload():
    body = {"output": [{"type": "reasoning"}, {"type": "message", "content": [{"type": "output_text", "text": "Hi"}]}]}
    assert extract_text(body) == "Hi"


def test_missing_key():
    with pytest.raises(MetaAPIError) as e:
        MetaClient(Settings("", "u", "m")).generate("x")
    assert e.value.kind == "missing_api_key"


@pytest.mark.parametrize("code,kind", [(401, "invalid_api_key"), (402, "billing"), (403, "access_denied"),
                                       (404, "not_found"), (429, "rate_limited"), (400, "invalid_request"), (500, "server_error")])
def test_http_errors_raise(code, kind):
    with patch("core.meta_client.requests.post", return_value=resp(code, {"error": {"message": "boom"}})):
        with pytest.raises(MetaAPIError) as e:
            MetaClient(S).generate("x")
    assert e.value.kind == kind


def test_network_error():
    with patch("core.meta_client.requests.post", side_effect=requests.exceptions.ConnectionError()):
        with pytest.raises(MetaAPIError) as e:
            MetaClient(S).generate("x")
    assert e.value.kind == "network"


def test_unexpected_structure():
    with patch("core.meta_client.requests.post", return_value=resp(200, {"foo": 1})):
        with pytest.raises(MetaAPIError) as e:
            MetaClient(S).generate("x")
    assert e.value.kind == "bad_response"
