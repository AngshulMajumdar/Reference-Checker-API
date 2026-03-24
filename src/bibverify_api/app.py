from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from bibverify.cache import JsonCache
from bibverify.pipeline import VerificationPipeline
from bibverify.providers.crossref_provider import CrossrefProvider
from bibverify.providers.openalex_provider import OpenAlexProvider
from bibverify.providers.semantic_scholar_provider import SemanticScholarProvider
from bibverify.llm.judge import HuggingFaceJudge

ALLOWED_SUFFIXES = {'.bib', '.txt', '.pdf', '.docx'}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_pipeline(storage_dir: Path, include_semantic_scholar: bool = False, enable_hf_judge: bool = False) -> VerificationPipeline:
    cache = JsonCache(storage_dir / 'cache' / 'provider_cache.json')
    mailto = os.environ.get('BIBVERIFY_MAILTO', 'user@example.com')
    providers = [
        CrossrefProvider(mailto=mailto, cache=cache),
        OpenAlexProvider(mailto=mailto, cache=cache),
    ]
    if include_semantic_scholar or os.environ.get('SEMANTIC_SCHOLAR_API_KEY'):
        providers.append(SemanticScholarProvider(cache=cache))

    judge = None
    if enable_hf_judge:
        model_name = os.environ.get('BIBVERIFY_HF_MODEL', 'TinyLlama/TinyLlama-1.1B-Chat-v1.0')
        judge = HuggingFaceJudge(model_name=model_name)

    return VerificationPipeline(providers=providers, judge=judge)


def _write_job_bundle(job_dir: Path) -> Path:
    bundle = job_dir / 'artifacts.zip'
    with ZipFile(bundle, 'w', ZIP_DEFLATED) as zf:
        for rel in [
            'output/corrected.bib',
            'output/report.csv',
            'output/changes.json',
            'output/diff_report.html',
            'job.json',
        ]:
            p = job_dir / rel
            if p.exists():
                zf.write(p, arcname=rel)
    return bundle


def _save_upload(job_dir: Path, upload: UploadFile) -> Path:
    suffix = Path(upload.filename or '').suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f'Unsupported file type: {suffix or "unknown"}. Allowed: {sorted(ALLOWED_SUFFIXES)}')
    input_dir = job_dir / 'input'
    input_dir.mkdir(parents=True, exist_ok=True)
    dest = input_dir / (Path(upload.filename).name or f'input{suffix}')
    with dest.open('wb') as f:
        shutil.copyfileobj(upload.file, f)
    return dest


def create_app(*, providers=None, judge=None, storage_dir: Optional[str | Path] = None) -> FastAPI:
    app = FastAPI(title='BibVerify API', version='1.0.0', description='Standalone API for bibliographic verification from BibTeX, TXT, PDF, or DOCX.')
    root = Path(storage_dir or os.environ.get('BIBVERIFY_STORAGE_DIR', './storage')).resolve()
    root.mkdir(parents=True, exist_ok=True)
    jobs_dir = root / 'jobs'
    jobs_dir.mkdir(exist_ok=True)

    @app.get('/health')
    def health():
        return {'status': 'ok', 'storage_dir': str(root)}

    @app.get('/providers')
    def providers_info():
        out = [
            {'name': 'crossref', 'enabled': True},
            {'name': 'openalex', 'enabled': True},
            {'name': 'semantic_scholar', 'enabled': bool(os.environ.get('SEMANTIC_SCHOLAR_API_KEY'))},
        ]
        return {'providers': out}

    @app.post('/api/v1/verify')
    async def verify_document(
        file: UploadFile = File(...),
        include_semantic_scholar: bool = Form(False),
        enable_hf_judge: bool = Form(False),
    ):
        job_id = uuid.uuid4().hex
        job_dir = jobs_dir / job_id
        output_dir = job_dir / 'output'
        output_dir.mkdir(parents=True, exist_ok=True)

        input_path = _save_upload(job_dir, file)

        metadata = {
            'job_id': job_id,
            'filename': input_path.name,
            'created_at': _utc_now(),
            'status': 'running',
            'include_semantic_scholar': include_semantic_scholar,
            'enable_hf_judge': enable_hf_judge,
        }
        (job_dir / 'job.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')

        try:
            pipeline = VerificationPipeline(providers=providers, judge=judge) if providers is not None else build_pipeline(root, include_semantic_scholar, enable_hf_judge)
            result = pipeline.verify_file(str(input_path), str(output_dir))
            metadata.update({
                'status': 'completed',
                'completed_at': _utc_now(),
                'summary': result.get('summary', {}),
                'artifacts': {
                    'corrected_bib': f'/api/v1/jobs/{job_id}/artifacts/corrected.bib',
                    'report_csv': f'/api/v1/jobs/{job_id}/artifacts/report.csv',
                    'changes_json': f'/api/v1/jobs/{job_id}/artifacts/changes.json',
                    'diff_report_html': f'/api/v1/jobs/{job_id}/artifacts/diff_report.html',
                    'bundle_zip': f'/api/v1/jobs/{job_id}/bundle',
                },
            })
        except Exception as exc:
            metadata.update({'status': 'failed', 'completed_at': _utc_now(), 'error': str(exc)})
            (job_dir / 'job.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            raise HTTPException(status_code=500, detail={'job_id': job_id, 'error': str(exc)}) from exc

        _write_job_bundle(job_dir)
        (job_dir / 'job.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
        return JSONResponse(metadata)

    @app.get('/api/v1/jobs/{job_id}')
    def get_job(job_id: str):
        job_file = jobs_dir / job_id / 'job.json'
        if not job_file.exists():
            raise HTTPException(status_code=404, detail='Job not found')
        return json.loads(job_file.read_text(encoding='utf-8'))

    @app.get('/api/v1/jobs/{job_id}/artifacts/{artifact_name}')
    def get_artifact(job_id: str, artifact_name: str):
        allowed = {'corrected.bib', 'report.csv', 'changes.json', 'diff_report.html'}
        if artifact_name not in allowed:
            raise HTTPException(status_code=404, detail='Artifact not found')
        path = jobs_dir / job_id / 'output' / artifact_name
        if not path.exists():
            raise HTTPException(status_code=404, detail='Artifact not found')
        media_type = {
            'corrected.bib': 'text/plain',
            'report.csv': 'text/csv',
            'changes.json': 'application/json',
            'diff_report.html': 'text/html',
        }[artifact_name]
        return FileResponse(path, media_type=media_type, filename=artifact_name)

    @app.get('/api/v1/jobs/{job_id}/bundle')
    def get_bundle(job_id: str):
        path = jobs_dir / job_id / 'artifacts.zip'
        if not path.exists():
            raise HTTPException(status_code=404, detail='Bundle not found')
        return FileResponse(path, media_type='application/zip', filename=f'{job_id}_artifacts.zip')

    return app
