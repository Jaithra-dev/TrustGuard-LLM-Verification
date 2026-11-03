"""Phase 2 check: one live API call. Run from project root:  python -m scripts.test_meta_api"""
from config.settings import get_settings
from core.meta_client import MetaClient, MetaAPIError

s = get_settings()
print(f"Endpoint: {s.base_url}/responses\nModel:    {s.model}\nKey set:  {bool(s.api_key)}")
try:
    print("\nModel reply:", MetaClient(s).generate("Reply with exactly: TrustGuard online"))
except MetaAPIError as e:
    print("\nFAILED:", e)
