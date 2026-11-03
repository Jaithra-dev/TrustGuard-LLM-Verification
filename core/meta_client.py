"""Meta Model API client (Responses API: POST {base}/responses).

Errors are raised as MetaAPIError so they can never be mistaken for a model answer.
"""
from typing import Optional
import requests
from config.settings import Settings, get_settings


class MetaAPIError(Exception):
    def __init__(self, kind: str, message: str, status: Optional[int] = None):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.message = message

    def __str__(self):
        s = f" (HTTP {self.status})" if self.status else ""
        return f"[{self.kind}]{s} {self.message}"


_STATUS_KINDS = {
    400: ("invalid_request", "Request was rejected as invalid. Check model name and request format."),
    401: ("invalid_api_key", "API key is invalid or missing."),
    402: ("billing", "Billing or credit problem on the Meta account."),
    403: ("access_denied", "Your key has no access to this model or resource."),
    404: ("not_found", "Endpoint or model not found. Check MODEL_API_BASE_URL and MODEL_NAME."),
    429: ("rate_limited", "Rate limit hit. Wait a moment and retry."),
}


def _server_message(resp: requests.Response) -> str:
    try:
        body = resp.json()
        err = body.get("error", body)
        if isinstance(err, dict):
            return str(err.get("message") or err)
        return str(err)
    except Exception:
        return (resp.text or "")[:300]


def extract_text(data: dict) -> str:
    """Pull the answer text out of a Responses-API payload."""
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()
    parts = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue  # skip reasoning items etc.
        for c in item.get("content") or []:
            if isinstance(c, dict) and c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    text = "\n".join(parts).strip()
    if not text:
        raise MetaAPIError("bad_response", "API returned no text. Unexpected response structure.")
    return text


class MetaClient:
    def __init__(self, settings: Optional[Settings] = None):
        self.s = settings or get_settings()

    def generate(self, prompt: str, instructions: Optional[str] = None) -> str:
        if not self.s.api_key:
            raise MetaAPIError("missing_api_key", "MODEL_API_KEY is not set. Add it to your .env file.")
        payload = {"model": self.s.model, "input": prompt}
        if instructions:
            payload["instructions"] = instructions
        try:
            resp = requests.post(
                f"{self.s.base_url}/responses",
                headers={"Authorization": f"Bearer {self.s.api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=self.s.timeout,
            )
        except requests.exceptions.Timeout:
            raise MetaAPIError("network", "Request timed out.")
        except requests.exceptions.RequestException as e:
            raise MetaAPIError("network", f"Network error: {e.__class__.__name__}")

        if resp.status_code != 200:
            kind, msg = _STATUS_KINDS.get(
                resp.status_code,
                ("server_error" if resp.status_code >= 500 else "http_error", "Unexpected API error."),
            )
            raise MetaAPIError(kind, f"{msg} Server said: {_server_message(resp)}", resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise MetaAPIError("bad_response", "API returned non-JSON content.", resp.status_code)
        return extract_text(data)
