"""Network utilities for dynamic port resolution."""

import logging
import os
import socket

logger = logging.getLogger("isekai.network")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a network port is already in use on the given host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def find_available_port(
    start_port: int = 8000, max_attempts: int = 50, host: str = "127.0.0.1"
) -> int:
    """Find the first available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if not is_port_in_use(port, host):
            return port
    raise RuntimeError(
        f"No available port found in range {start_port} to {start_port + max_attempts - 1}"
    )


def resolve_server_port(preferred_port: int = 8000, host: str = "127.0.0.1") -> int:
    """Resolve port dynamically.

    Respects explicit env vars (PORT, API_PORT) if available;
    falls back to the next free port if preferred_port is occupied.
    """
    bind_host = "127.0.0.1" if host in ("0.0.0.0", "") else host

    env_port_str = os.environ.get("PORT") or os.environ.get("API_PORT")
    if env_port_str:
        try:
            env_port = int(env_port_str)
            if not is_port_in_use(env_port, bind_host):
                return env_port
            logger.warning(
                "Configured port %d from environment is already in use. Searching for free port...",
                env_port,
            )
            return find_available_port(start_port=env_port + 1, host=bind_host)
        except ValueError:
            logger.warning(
                "Invalid port in environment: %s. Using dynamic resolution.",
                env_port_str,
            )

    if not is_port_in_use(preferred_port, bind_host):
        return preferred_port

    free_port = find_available_port(start_port=preferred_port + 1, host=bind_host)
    logger.info(
        "Port %d is already in use. Dynamically resolved to port %d.",
        preferred_port,
        free_port,
    )
    return free_port
