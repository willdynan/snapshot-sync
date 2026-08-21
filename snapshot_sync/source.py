"""Paginated source client.

Retry policy: 429 sleeps what the source asks (Retry-After, capped) — the
source knows its limits and you do not. Transient 5xx and network errors get
bounded exponential backoff. Anything persistent raises: a sync that loops
forever is an outage nobody pages on.
"""

import json
import time
import urllib.error
import urllib.request


class SourceError(RuntimeError):
    pass


MAX_RETRIES = 5
RETRY_AFTER_CAP = 30.0
BACKOFF_BASE = 0.05
REQUEST_TIMEOUT = 20.0  # an unbounded network call is a hang nobody pages on


def _get(url: str, sleeper=time.sleep) -> dict:
    for attempt in range(MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < MAX_RETRIES:
                sleeper(min(float(exc.headers.get("Retry-After", "1")), RETRY_AFTER_CAP))
                continue
            if 500 <= exc.code < 600 and attempt < MAX_RETRIES:
                sleeper(BACKOFF_BASE * (2 ** attempt))
                continue
            raise SourceError(f"GET {url} -> HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            if attempt < MAX_RETRIES:
                sleeper(BACKOFF_BASE * (2 ** attempt))
                continue
            raise SourceError(f"GET {url} -> {exc.reason}") from exc
    raise SourceError(f"GET {url}: gave up after {MAX_RETRIES + 1} attempts")


def fetch_all(base_url: str, page_size: int = 50, sleeper=time.sleep):
    page = 1
    while page is not None:
        data = _get(f"{base_url}/items?page={page}&page_size={page_size}", sleeper)
        yield from data["items"]
        page = data.get("next_page")
