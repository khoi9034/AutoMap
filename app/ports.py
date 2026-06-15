"""Port defaults and startup guards for AutoMap."""

from __future__ import annotations

import socket


AUTOMAP_FRONTEND_PORT = 3010
AUTOMAP_BACKEND_PORT = 8010
CFS_RESERVED_FRONTEND_PORT = 3000
CFS_RESERVED_BACKEND_PORT = 8000
CFS_RESERVED_PORTS = {CFS_RESERVED_FRONTEND_PORT, CFS_RESERVED_BACKEND_PORT}
CFS_RESERVED_WARNING = "Ports 3000 and 8000 are reserved for Cabarrus FutureScape."


def is_port_busy(port: int, host: str = "127.0.0.1") -> bool:
    """Return true when a TCP port is already accepting connections."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, int(port))) == 0


def validate_automap_port(port: int, *, service_name: str, host: str = "127.0.0.1") -> list[str]:
    """Validate an AutoMap startup port and return non-fatal reserved-port warnings."""
    selected_port = int(port)
    warnings: list[str] = []
    for reserved_port in sorted(CFS_RESERVED_PORTS):
        if is_port_busy(reserved_port, host=host):
            warnings.append(f"{CFS_RESERVED_WARNING} Detected port {reserved_port} in use.")
    if selected_port in CFS_RESERVED_PORTS:
        raise ValueError(f"{CFS_RESERVED_WARNING} AutoMap {service_name} cannot bind to port {selected_port}.")
    if is_port_busy(selected_port, host=host):
        raise ValueError(f"AutoMap {service_name} port {selected_port} is already in use.")
    return warnings
