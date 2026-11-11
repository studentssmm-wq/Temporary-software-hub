"""Environment settings. Local secrets are never embedded in source."""
import os
import hashlib
import re
from urllib.parse import urlsplit
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if os.getenv("PROFKOM_TEST_MODE") != "1":
    load_dotenv(PROJECT_ROOT / os.getenv("PROFKOM_ENV_FILE", ".env"))

def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    if value.lower().strip() not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} must be true or false")
    return value.lower().strip() in {"true", "1", "yes"}

APP_ENV = os.getenv("APP_ENV", "production").strip().lower()
IS_DEVELOPMENT = APP_ENV != "production"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MONO_JAR_URL = os.getenv("MONO_JAR_URL", "")
ADMIN_IDS = frozenset(int(value.strip()) for value in os.getenv("ADMIN_IDS", "").split(",") if value.strip())
ENABLE_MAILINGS = env_flag("ENABLE_MAILINGS", not IS_DEVELOPMENT)
ENABLE_PAYMENTS = env_flag("ENABLE_PAYMENTS", not IS_DEVELOPMENT)
ENABLE_SHEETS = env_flag("ENABLE_SHEETS", not IS_DEVELOPMENT)
EXPECTED_DATABASE_HOST = os.getenv("EXPECTED_DATABASE_HOST", "").strip() or urlsplit(DATABASE_URL).hostname or ""
DATABASE_SCHEMA = os.getenv("DATABASE_SCHEMA", "public").strip()
if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", DATABASE_SCHEMA):
    raise ValueError("Invalid DATABASE_SCHEMA")


def validate_settings() -> None:
    if APP_ENV not in {'production', 'development'}:
        raise ValueError('APP_ENV must be production or development')
    validate_integrations()
    if not EXPECTED_DATABASE_HOST:
        raise ValueError('Set EXPECTED_DATABASE_HOST to the intended database hostname')
    if not BOT_TOKEN or not DATABASE_URL:
        raise ValueError("Set BOT_TOKEN and DATABASE_URL in your local .env")
    if IS_DEVELOPMENT and urlsplit(DATABASE_URL).hostname != "127.0.0.1":
        raise ValueError("Development bot uses localhost only; Neon development connections are disabled")
    if IS_DEVELOPMENT and DATABASE_SCHEMA == "public":
        raise ValueError("Development requires a separate local schema")
    if IS_DEVELOPMENT and not EXPECTED_DATABASE_HOST:
        raise ValueError("Set EXPECTED_DATABASE_HOST to the verified development branch hostname")
    if IS_DEVELOPMENT and (ENABLE_MAILINGS or ENABLE_PAYMENTS or ENABLE_SHEETS):
        raise ValueError("External mailings, payments and Sheets must remain disabled in development")


def validate_integrations() -> None:
    import json
    if ENABLE_PAYMENTS:
        base = urlsplit(os.getenv('WEB_APP_URL', ''))
        if base.scheme != 'https' or not base.hostname or base.username or base.password or base.query or base.fragment:
            raise ValueError('WEB_APP_URL must be the public HTTPS API address without credentials, query or fragment')
        if not os.getenv('MONO_TOKEN', '').strip():
            raise ValueError('Set MONO_TOKEN for payment webhook registration')
    if ENABLE_SHEETS:
        if not os.getenv('SPREADSHEET_URL', '').startswith('https://docs.google.com/spreadsheets/'):
            raise ValueError('Set SPREADSHEET_URL to the Google spreadsheet URL')
        try:
            credentials = json.loads(os.getenv('GOOGLE_CREDS_JSON', ''))
            if not isinstance(credentials, dict) or not all(credentials.get(key) for key in ('client_email','private_key','token_uri')):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('GOOGLE_CREDS_JSON must be the complete service account JSON') from None


def mono_webhook_secret():
    return os.getenv('MONO_WEBHOOK_SECRET', '') or (hashlib.sha256(('profkom:mono:webhook:'+BOT_TOKEN).encode()).hexdigest() if BOT_TOKEN else '')
