from __future__ import annotations
import time
from typing import List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ..models import BibEntry, CandidateRecord
from ..cache import JsonCache


class BaseProvider:
    name = "base"

    def __init__(self, timeout: int = 20, min_interval: float = 0.2, cache: JsonCache | None = None):
        self.timeout = timeout
        self.min_interval = min_interval
        self.cache = cache
        self._last_call_ts = 0.0
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.6, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def _throttle(self) -> None:
        delta = time.time() - self._last_call_ts
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last_call_ts = time.time()

    def _cache_get(self, payload: dict):
        if not self.cache:
            return None, None
        key = JsonCache.stable_key(self.name, payload)
        return key, self.cache.get(key)

    def _cache_set(self, key: str | None, value):
        if self.cache and key is not None:
            self.cache.set(key, value)

    def search(self, entry: BibEntry) -> List[CandidateRecord]:
        raise NotImplementedError
