# STATUS: COMPLETE
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemma 4 models via Gemini API (256K context window each)
GEMMA_MODEL_BULK = os.getenv("GEMMA_MODEL_BULK", "gemma-4-26b-a4b-it")
GEMMA_MODEL_ANALYZE = os.getenv("GEMMA_MODEL_ANALYZE", "gemma-4-31b-it")
GEMMA_CONTEXT_TOKENS = int(os.getenv("GEMMA_CONTEXT_TOKENS", "262144"))
# Bulk JSON replies are small; 16K output tokens can trigger Gemma API 500 errors.
GEMMA_MAX_OUTPUT_TOKENS_BULK = int(os.getenv("GEMMA_MAX_OUTPUT_TOKENS_BULK", "2048"))
GEMMA_MAX_OUTPUT_TOKENS_ANALYZE = int(os.getenv("GEMMA_MAX_OUTPUT_TOKENS_ANALYZE", "8192"))

# Rate limit — default 12 for free tier (15 RPM cap); raise on paid tier via env
AI_REQUESTS_PER_MINUTE = int(os.getenv("AI_REQUESTS_PER_MINUTE", "12"))

# Per-run caps — raise M2_MAX_BATCHES_PER_RUN after upgrading Gemini API tier
M2_BATCH_SIZE = int(os.getenv("M2_BATCH_SIZE", "8"))
M2_MAX_BATCHES_PER_RUN = int(os.getenv("M2_MAX_BATCHES_PER_RUN", "30"))
M2_REEXPAND_DAYS = int(os.getenv("M2_REEXPAND_DAYS", "7"))
M3_MAX_KEYWORDS_PER_RUN = int(os.getenv("M3_MAX_KEYWORDS_PER_RUN", "5"))
M3_BATCH_SIZE = int(os.getenv("M3_BATCH_SIZE", "1"))
# Google Trends (pytrends) — strict on datacenter IPs; use long delays on Render
M3_PYTRENDS_DELAY_SEC = int(os.getenv("M3_PYTRENDS_DELAY_SEC", "45"))
M3_PYTRENDS_TIMEOUT_SEC = int(os.getenv("M3_PYTRENDS_TIMEOUT_SEC", "45"))
M3_PYTRENDS_MAX_RETRIES = int(os.getenv("M3_PYTRENDS_MAX_RETRIES", "2"))
M3_PYTRENDS_429_BACKOFF_SEC = int(os.getenv("M3_PYTRENDS_429_BACKOFF_SEC", "90"))
M3_PYTRENDS_429_ABORT_AFTER = int(os.getenv("M3_PYTRENDS_429_ABORT_AFTER", "2"))
# When Google blocks Trends on Render, estimate scores via AI (uses Gemini quota)
M3_AI_ESTIMATE_ON_TRENDS_FAIL = os.getenv("M3_AI_ESTIMATE_ON_TRENDS_FAIL", "true").lower() in (
    "1",
    "true",
    "yes",
)
M3_AI_ESTIMATE_MAX_PER_RUN = int(os.getenv("M3_AI_ESTIMATE_MAX_PER_RUN", "3"))
M4_MAX_KEYWORDS_PER_RUN = int(os.getenv("M4_MAX_KEYWORDS_PER_RUN", "30"))
M7_MAX_KEYWORDS_PER_RUN = int(os.getenv("M7_MAX_KEYWORDS_PER_RUN", "30"))

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AOIP/1.0")
BACKEND_SECRET = os.getenv("BACKEND_SECRET", "changeme")
ENV = os.getenv("ENV", "development")

# Comma-separated allowed origins for CORS, e.g. https://your-app.vercel.app
# Falls back to FRONTEND_URL, then "*" if unset.
_cors_raw = os.getenv("CORS_ORIGINS", "")
FRONTEND_URL = os.getenv("FRONTEND_URL", "").rstrip("/")
CORS_ORIGINS = [o.strip().rstrip("/") for o in _cors_raw.split(",") if o.strip()]
if not CORS_ORIGINS and FRONTEND_URL:
    CORS_ORIGINS = [FRONTEND_URL]

_REDDIT_PLACEHOLDERS = {
    "",
    "your_reddit_client_id",
    "your_reddit_client_secret",
}


def is_reddit_configured() -> bool:
    """True when real Reddit API credentials are set (not empty or placeholder)."""
    return (
        REDDIT_CLIENT_ID not in _REDDIT_PLACEHOLDERS
        and REDDIT_CLIENT_SECRET not in _REDDIT_PLACEHOLDERS
    )

# Safety check — crash early if critical vars are missing
for var_name, var_val in [
    ("SUPABASE_URL", SUPABASE_URL),
    ("SUPABASE_SERVICE_KEY", SUPABASE_SERVICE_KEY),
    ("GEMINI_API_KEY", GEMINI_API_KEY),
]:
    if not var_val:
        raise EnvironmentError(f"Missing required environment variable: {var_name}")
