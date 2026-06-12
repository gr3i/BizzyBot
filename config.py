import os
from dotenv import load_dotenv

load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


class Config:
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    guild_id: int = int(os.getenv("GUILD_ID", "0") or 0)

    # Old static token fallback
    vut_api_key: str = os.getenv("VUT_API_KEY", "")
    owner_id: int = int(os.getenv("OWNER_ID", "0") or 0)

    # New client credentials auth
    vut_use_client_credentials: bool = env_bool("VUT_USE_CLIENT_CREDENTIALS", False)
    vut_allow_static_token_fallback: bool = env_bool("VUT_ALLOW_STATIC_TOKEN_FALLBACK", True)

    vut_client_id: str = os.getenv("VUT_CLIENT_ID", "")
    vut_client_secret: str = os.getenv("VUT_CLIENT_SECRET", "")
    vut_token_url: str = os.getenv("VUT_TOKEN_URL", "")
    vut_api_base: str = os.getenv("VUT_API_BASE", "https://www.vut.cz/api/person/v1")
