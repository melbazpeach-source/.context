"""Enable the default Sirens MISP feeds.

Idempotent: finds feeds by provider/name and toggles enabled=True +
caching_enabled=True. Triggers an immediate fetch once on first enable.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from pymisp import PyMISP


# Feeds identified by (provider, url) — MISP seeds these by default during
# first-run. If a feed is missing, the script will print a clear error rather
# than try to create it (creation requires the full provenance block that
# ships with MISP itself).
DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("CIRCL",      "https://www.circl.lu/doc/misp/feed-osint"),
    ("Botvrij.eu", "https://www.botvrij.eu/data/feed-osint"),
    ("abuse.ch",   "https://sslbl.abuse.ch/blacklist/sslipblacklist.csv"),
    ("abuse.ch",   "https://urlhaus.abuse.ch/downloads/csv_recent/"),
    ("abuse.ch",   "https://feodotracker.abuse.ch/downloads/ipblocklist.csv"),
]


def main() -> int:
    url = os.environ["MISP_URL"]
    key = os.environ["MISP_ADMIN_KEY"]
    verify_tls = os.environ.get("MISP_VERIFY_TLS", "false").lower() == "true"

    misp = PyMISP(url, key, verify_tls)

    all_feeds: list[dict[str, Any]] = misp.feeds(pythonify=False)  # type: ignore[assignment]
    by_key: dict[tuple[str, str], dict[str, Any]] = {
        (f["Feed"]["provider"], f["Feed"]["url"].rstrip("/")): f["Feed"]
        for f in all_feeds
    }

    exit_code = 0
    for provider, feed_url in DEFAULT_FEEDS:
        key_ = (provider, feed_url.rstrip("/"))
        feed = by_key.get(key_)
        if feed is None:
            print(f"MISS   {provider} {feed_url}  (not present; check MISP seed)")
            exit_code = 2
            continue

        fid = feed["id"]
        already = feed.get("enabled") and feed.get("caching_enabled")
        if already:
            print(f"SKIP   id={fid} {provider} {feed_url} (enabled)")
            continue

        misp.enable_feed(fid)
        misp.enable_feed_cache(fid)
        misp.fetch_feed(fid)
        print(f"ENABLE id={fid} {provider} {feed_url}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
