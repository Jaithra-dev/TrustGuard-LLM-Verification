"""Central configuration. Reads environment variables / .env (never hardcode keys)."""
import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    timeout: int = 60


def get_settings() -> Settings:
    # override=True so edits to .env are picked up on Streamlit reruns
    load_dotenv(override=True)
    return Settings(
        api_key=os.getenv("MODEL_API_KEY", "").strip(),
        base_url=os.getenv("MODEL_API_BASE_URL", "https://api.meta.ai/v1").strip().rstrip("/"),
        model=os.getenv("MODEL_NAME", "muse-spark-1.2").strip(),
    )
