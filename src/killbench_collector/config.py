"""Load configuration and environment for the standalone collector."""

from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

for dotenv_path in (PROJECT_ROOT / ".env", PROJECT_ROOT.parent / ".env"):
    load_dotenv(dotenv_path)

with CONFIG_PATH.open() as f:
    _CFG = yaml.safe_load(f)

# API
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = _CFG["api"]["base_url"]
CONCURRENCY_LIMIT = _CFG["api"]["concurrency"]
MAX_RETRIES = _CFG["api"]["max_retries"]
RETRY_BASE_DELAY = _CFG["api"]["retry_base_delay"]

# Bench
N_REROLLS = _CFG["bench"]["n_rerolls"]
BENCH_MODELS = _CFG["models"]
BENCH_REASONING = set(_CFG["bench"].get("reasoning_models", []))

# Dimensions
NATIONALITIES = _CFG["nationalities"]
RELIGIONS = _CFG["religions"]
GENDERS = _CFG["genders"]
AGES = _CFG["ages"]
ROLES = _CFG["roles"]
SKIN_COLORS = _CFG["skin_colors"]
BODY_TYPES = _CFG["body_types"]
PHONE_PLATFORMS = _CFG["phone_platforms"]
SEXUAL_ORIENTATIONS = _CFG["sexual_orientations"]
GENDER_IDENTITIES = _CFG["gender_identities"]
POLITICAL_VIEWS = _CFG["political_views"]
COMBO_PAIRS = _CFG.get("combo_pairs", [])

# Lookup: dimension key -> values list
DIMENSION_VALUES = {
    "nationality": NATIONALITIES,
    "religion": RELIGIONS,
    "skin_color": SKIN_COLORS,
    "body_type": BODY_TYPES,
    "phone": PHONE_PLATFORMS,
    "orientation": SEXUAL_ORIENTATIONS,
    "gender_identity": GENDER_IDENTITIES,
    "politics": POLITICAL_VIEWS,
}
