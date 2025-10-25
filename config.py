import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    guild_id: int = int(os.getenv("GUILD_ID", "0") or 0)
    vut_api_key: str = os.getenv("VUT_API_KEY", "")
    owner_id: int = int(os.getenv("OWNER_ID", "0") or 0)
