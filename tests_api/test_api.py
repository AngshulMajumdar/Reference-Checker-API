from pathlib import Path
from fastapi.testclient import TestClient
from bibverify_api import create_app
from bibverify.models import CandidateRecord
from bibverify.providers.mock_provider import MockProvider


def test_verify_endpoint(tmp_path: Path):
    catalog = {
        'a theory of deep learning': [CandidateRecord(source='mock', title='A Theory of Deep Learning', authors=['Alice Doe'], year='2021', venue='Journal X')]
    }
    app = create_app(providers=[MockProvider(catalog)], storage_dir=tmp_path)
    client = TestClient(app)
    sample = """@article{toy1,\n  author = {Doe, Alice},\n  title = {A theory of deep learning},\n  year = {2021}\n}\n"""
    files = {'file': ('sample.bib', sample, 'text/plain')}
    r = client.post('/api/v1/verify', files=files)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['status'] == 'completed'
    assert 'bundle_zip' in data['artifacts']
    bundle = client.get(data['artifacts']['bundle_zip'])
    assert bundle.status_code == 200
