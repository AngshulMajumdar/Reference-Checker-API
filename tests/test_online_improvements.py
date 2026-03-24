from pathlib import Path
from bibverify.cache import JsonCache
from bibverify.providers.crossref_provider import CrossrefProvider
from bibverify.models import BibEntry


class DummyResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_code = 200
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


def test_json_cache_roundtrip(tmp_path):
    cache = JsonCache(tmp_path / 'cache.json')
    key = JsonCache.stable_key('x', {'a': 1})
    assert cache.get(key) is None
    cache.set(key, {'ok': True})
    cache2 = JsonCache(tmp_path / 'cache.json')
    assert cache2.get(key) == {'ok': True}


def test_crossref_uses_cache(tmp_path, monkeypatch):
    cache = JsonCache(tmp_path / 'cache.json')
    provider = CrossrefProvider(cache=cache)
    calls = {'n': 0}
    payload = {'message': {'items': [{'title': ['Deep Learning'], 'author': [{'given': 'Ian', 'family': 'Goodfellow'}], 'DOI': '10.1/x'}]}}
    def fake_get(*args, **kwargs):
        calls['n'] += 1
        return DummyResponse(payload)
    monkeypatch.setattr(provider.session, 'get', fake_get)
    entry = BibEntry(entry_type='article', entry_key='k', fields={'title': 'Deep Learning', 'author': 'Goodfellow, Ian'}, raw_entry={})
    first = provider.search(entry)
    second = provider.search(entry)
    assert len(first) == 1
    assert len(second) == 1
    assert calls['n'] == 1
