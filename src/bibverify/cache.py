from __future__ import annotations
import json
import hashlib
import threading
from pathlib import Path
from typing import Any


class JsonCache:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    @staticmethod
    def stable_key(namespace: str, payload: dict[str, Any]) -> str:
        raw = json.dumps({"ns": namespace, "payload": payload}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str):
        return self._data.get(key)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._data[key] = value
            tmp = self.path.with_suffix(self.path.suffix + '.tmp')
            tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding='utf-8')
            tmp.replace(self.path)
