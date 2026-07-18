from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    host: str = os.getenv("QUOTEOPS_HOST", "0.0.0.0")
    port: int = int(os.getenv("QUOTEOPS_PORT", "8765"))
    env: str = os.getenv("QUOTEOPS_ENV", "dev")
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
    ralfia_api_base: str = os.getenv("RALFIA_API_BASE", "http://127.0.0.1:8099")
    ralfia_ops_base_url: str = os.getenv("RALFIA_OPS_BASE_URL", "http://127.0.0.1:2002")
    smart_quoter_base_url: str = os.getenv("SMART_QUOTER_BASE_URL", "http://127.0.0.1:2026")
    ralfia_mcp_url: str = os.getenv("RALFIA_MCP_URL", "http://127.0.0.1:8102/mcp")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-5.6")
    enable_openai: bool = os.getenv("QUOTEOPS_ENABLE_OPENAI", "0").lower() in {"1", "true", "yes", "on"}
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ruc_api_token_base_url: str = os.getenv(
        "RUC_API_TOKEN_BASE_URL", "https://consulta-ruc-token.azurewebsites.net"
    )
    ruc_api_lookup_base_url: str = os.getenv(
        "RUC_API_LOOKUP_BASE_URL", "https://consulta-ruc.azurewebsites.net"
    )
    ruc_api_username: str = os.getenv("RUC_API_USERNAME", "")
    ruc_api_password: str = os.getenv("RUC_API_PASSWORD", "")
    ruc_api_timeout_seconds: float = float(os.getenv("RUC_API_TIMEOUT_SECONDS", "12"))
    ruc_api_cache_ttl_seconds: int = int(os.getenv("RUC_API_CACHE_TTL_SECONDS", "900"))
    ruc_api_live_enabled: bool = os.getenv("RUC_API_LIVE_ENABLED", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    quoteops_mongo_db: str = os.getenv("QUOTEOPS_MONGO_DB", "ralphiia_quoteops_staging")
    quoteops_artifact_root: str = os.getenv("QUOTEOPS_ARTIFACT_ROOT", "/tmp/ralphiia-quoteops-artifacts")
    quoteops_webhook_secret: str = os.getenv("QUOTEOPS_WEBHOOK_SECRET", "")
    quoteops_mcp_api_key: str = os.getenv("QUOTEOPS_MCP_API_KEY", "")
    iess_evidence_root: str = os.getenv("IESS_EVIDENCE_ROOT", "/home/rlopez/data/ralphiia-quoteops/iess-evidence")
    ralfia_package_root: str = os.getenv(
        "RALFIA_PACKAGE_ROOT", "/home/rlopez/projects/raphiia-openai"
    )
    allow_production_writes: bool = os.getenv("QUOTEOPS_ALLOW_PRODUCTION_WRITES", "0").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    remote_dev_demo_enabled: bool = os.getenv("REMOTE_DEV_DEMO_ENABLED", "0").lower() in {
        "1", "true", "yes", "on"
    }
    remote_dev_demo_mode: str = os.getenv("REMOTE_DEV_DEMO_MODE", "offline")
    remote_dev_mcp_url: str = os.getenv("REMOTE_DEV_MCP_URL", "http://127.0.0.1:8102/mcp")
    remote_dev_mcp_api_key: str = os.getenv("REMOTE_DEV_MCP_API_KEY", "")
    remote_dev_codex_bin: str = os.getenv("REMOTE_DEV_CODEX_BIN", "")
    remote_dev_execute_codex: bool = os.getenv("REMOTE_DEV_EXECUTE_CODEX", "0").lower() in {
        "1", "true", "yes", "on"
    }
    remote_dev_workspace_root: str = os.getenv("REMOTE_DEV_WORKSPACE_ROOT", "/tmp/ralfia-remote-dev-demo")
    remote_dev_timeout_seconds: int = int(os.getenv("REMOTE_DEV_TIMEOUT_SECONDS", "240"))
    remote_dev_whisper_url: str = os.getenv("REMOTE_DEV_WHISPER_URL", "http://127.0.0.1:9000")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
