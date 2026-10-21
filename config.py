import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # fine for tests
    pass

BASE_DIR = Path(__file__).parent
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
UMAMOE_API_KEY = os.getenv("API_KwhyEY", "")

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-8b")

UMAMOE_CIRCLE_URL = os.getenv("UMAMOE_CIRCLE_URL", "")
UMAMOE_USER_URL = os.getenv("UMAMOE_USER_URL", "")
CACHE_SECONDS = 300

# Comma-separated role names that are allowed to use !link and !unlink
# e.g. MOD_ROLE_NAMES=Mod,Staff,Admin
_raw_roles = os.getenv("MOD_ROLE_NAMES", "Mod,Staff")
MOD_ROLE_NAMES = {r.strip().lower() for r in _raw_roles.split(",") if r.strip()}

DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "manhattan.db"))
