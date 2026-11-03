"""Helpers for reading JSON out of model replies (which may include code fences or chatter)."""
import json
import re


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    return re.sub(r"\s*```$", "", text).strip()


def parse_json_array(text: str) -> list:
    t = _strip_fences(text)
    try:
        data = json.loads(t)
    except ValueError:
        start, end = t.find("["), t.rfind("]")
        if start == -1 or end <= start:
            raise ValueError("No JSON array found in model reply.")
        data = json.loads(t[start:end + 1])
    if not isinstance(data, list):
        raise ValueError("Model reply was not a JSON array.")
    return data