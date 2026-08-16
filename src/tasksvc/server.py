"""``http.server`` adapter around :mod:`tasksvc.api`.

Single threaded and deliberately boring: this service sits behind a reverse
proxy that terminates TLS and handles concurrency.
"""

import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from . import api, config, db

log = logging.getLogger("tasksvc")


class Handler(BaseHTTPRequestHandler):
    server_version = "tasksvc/0.3"

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""

        request = api.Request(
            method=method,
            path=parsed.path,
            query=query,
            headers=dict(self.headers.items()),
            body=body,
        )
        log.info(
            "request %s %s query=%s headers=%s",
            method,
            parsed.path,
            query,
            dict(self.headers.items()),
        )
        status, payload = api.handle(self.server.conn, request)

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def log_message(self, fmt: str, *args) -> None:
        log.info("%s - %s", self.address_string(), fmt % args)


def serve() -> None:
    logging.basicConfig(level=logging.INFO)
    conn = db.connect()
    db.init_schema(conn)

    httpd = HTTPServer((config.LISTEN_HOST, config.LISTEN_PORT), Handler)
    httpd.conn = conn
    log.info("listening on %s:%s", config.LISTEN_HOST, config.LISTEN_PORT)
    try:
        httpd.serve_forever()
    finally:
        conn.close()


if __name__ == "__main__":
    serve()
