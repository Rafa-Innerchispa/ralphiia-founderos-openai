from functools import lru_cache
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseModel):
    host: str = os.getenv("QUOTEOPS_HOST", "0.0.0.0")
    port: int = int(os.getenv("QUOTEOPS_PORT", "8765"))
    env: str = os.getenv("QUOTEOPS_ENV", "dev")
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    ralfia_api_base: str = os.getenv("RALFIA_API_BASE", "http://127.0.0.1:8099")
    ralfia_mcp_url: str = os.getenv("RALFIA_MCP_URL", "http://127.0.0.1:8102/mcp")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
