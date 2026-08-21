"""A deliberately flaky paginated source, for tests and demos.

Serves GET /items?page=N&page_size=M over 100 synthetic items. Fault injection:
`fail_first` answers 500 to the first N requests; `rate_limit_every` answers
429 (with Retry-After) to every kth request. The point of the demo is that the
sync completes anyway.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse


class MockSource(ThreadingHTTPServer):
    def __init__(self, addr=("127.0.0.1", 0), n_items=100, fail_first=0, rate_limit_every=0):
        self.items = [
            {"id": i, "name": f"item-{i:03d}", "group": ("red", "green", "blue")[i % 3]}
            for i in range(n_items)
        ]
        self.requests = 0
        self.fail_first = fail_first
        self.rate_limit_every = rate_limit_every
        super().__init__(addr, _Handler)

    @property
    def url(self) -> str:
        return f"http://{self.server_address[0]}:{self.server_address[1]}"


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        srv: MockSource = self.server
        srv.requests += 1
        if srv.requests <= srv.fail_first:
            self.send_response(500)
            self.end_headers()
            return
        if srv.rate_limit_every and srv.requests % srv.rate_limit_every == 0:
            self.send_response(429)
            self.send_header("Retry-After", "0.01")
            self.end_headers()
            return
        query = parse_qs(urlparse(self.path).query)
        page = int(query.get("page", ["1"])[0])
        page_size = int(query.get("page_size", ["50"])[0])
        start = (page - 1) * page_size
        chunk = srv.items[start:start + page_size]
        next_page = page + 1 if start + page_size < len(srv.items) else None
        body = json.dumps({"items": chunk, "next_page": next_page}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
