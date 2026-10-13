"""Process entry point for ``python -m apps.demo``."""

from __future__ import annotations

import os

from .server import create_server


def main() -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = create_server(host=host, port=port)
    address, actual_port = server.server_address[:2]
    print(f"SimTrouble Demo v0.1: http://{address}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
