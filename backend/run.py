"""Dynamic server launcher for Isekai RPG."""

import logging
import sys
import uvicorn
from app.core.config import settings
from app.core.network import resolve_server_port

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("isekai.launcher")


def main() -> None:
    # Allow command-line override: python run.py 8001
    preferred = settings.api_port
    if len(sys.argv) > 1:
        try:
            preferred = int(sys.argv[1])
        except ValueError:
            pass

    port = resolve_server_port(preferred_port=preferred, host=settings.api_host)
    display_host = (
        "localhost"
        if settings.api_host in ("0.0.0.0", "127.0.0.1", "")
        else settings.api_host
    )
    logger.info(
        "Starting Isekai Backend on http://%s:%d (bound to %s)",
        display_host,
        port,
        settings.api_host,
    )
    uvicorn.run("app.main:app", host=settings.api_host, port=port, reload=False)


if __name__ == "__main__":
    main()
