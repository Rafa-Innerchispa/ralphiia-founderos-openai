"""Entrypoint QuoteOps."""

import uvicorn

from quoteops.settings import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "quoteops.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
