"""Bounded, allowlisted HTTP reads with conditional caching and retries."""

import hashlib
import json
import re
import time
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import FeedCache, utcnow

HOSTS = {
    "api.ashbyhq.com",
    "boards-api.greenhouse.io",
    "api.lever.co",
    "api.eu.lever.co",
    "remotive.com",
    "www.arbeitnow.com",
    "remoteok.com",
    "api.adzuna.com",
    "hacker-news.firebaseio.com",
}


class FeedError(RuntimeError):
    pass


class FeedHTTP:
    def __init__(self, db: Session, client: httpx.Client | None = None, sleep=time.sleep):
        self.db, self.sleep = db, sleep
        self.client = client or httpx.Client(timeout=get_settings().ingestion_timeout, follow_redirects=False)
        self.owned = client is None
        self.last_request = 0.0

    def close(self):
        if self.owned:
            self.client.close()

    def get(self, url: str, params: dict | None = None):
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in HOSTS
            or parsed.username
            or parsed.port not in (None, 443)
        ):
            raise FeedError("Only configured official API hosts are permitted")
        key = hashlib.sha256((url + json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
        cached = self.db.get(FeedCache, key)
        now = utcnow()
        if cached and cached.expires_at.replace(tzinfo=timezone.utc) > now:
            return cached.payload
        headers = {"User-Agent": get_settings().ingestion_user_agent, "Accept": "application/json"}
        if cached:
            if cached.etag:
                headers["If-None-Match"] = cached.etag
            if cached.modified:
                headers["If-Modified-Since"] = cached.modified
        # Remotive asks for at most four reads daily. Retry on the next run,
        # rather than sending multiple requests when its service is unavailable.
        attempts = 1 if parsed.hostname == "remotive.com" else 3
        for attempt in range(attempts):
            delay = get_settings().ingestion_request_delay - (time.monotonic() - self.last_request)
            if delay > 0:
                self.sleep(delay)
            try:
                response = self.client.get(url, params=params, headers=headers)
                self.last_request = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    if attempts == 1:
                        raise FeedError("Source unavailable; defer to next scheduled run")
                    retry = response.headers.get("Retry-After", "")
                    if retry.isdigit():
                        wait = int(retry)
                    else:
                        try:
                            wait = max(0, (parsedate_to_datetime(retry) - now).total_seconds())
                        except (TypeError, ValueError):
                            wait = 2**attempt
                    if wait > 30:
                        raise FeedError("Source requested a longer retry delay; defer to next scheduled run")
                    self.sleep(wait)
                    continue
                if response.status_code == 304 and cached:
                    payload = cached.payload
                else:
                    if response.status_code != 200:
                        raise FeedError(f"Source returned HTTP {response.status_code}")
                    if len(response.content) > 30 * 1024 * 1024:
                        raise FeedError("Feed exceeds the 30 MB response limit")
                    payload = response.json()
                control = response.headers.get("Cache-Control", "")
                max_age = re.search(r"(?:s-maxage|max-age)=(\d+)", control)
                expiry = now + timedelta(seconds=int(max_age[1]) if max_age else 0)
                if not max_age and response.headers.get("Expires"):
                    try:
                        expiry = parsedate_to_datetime(response.headers["Expires"])
                    except (TypeError, ValueError):
                        pass
                if "no-cache" in control:
                    expiry = now
                if "no-store" not in control:
                    cached = cached or FeedCache(key=key)
                    cached.payload, cached.expires_at = payload, expiry
                    cached.etag = response.headers.get("ETag", cached.etag)
                    cached.modified = response.headers.get("Last-Modified", cached.modified)
                    self.db.add(cached)
                    self.db.flush()
                elif cached:
                    self.db.delete(cached)
                    self.db.flush()
                return payload
            except (httpx.TransportError, ValueError):
                if attempt < attempts - 1:
                    self.sleep(2**attempt)
        raise FeedError("Source unavailable after bounded attempts")
