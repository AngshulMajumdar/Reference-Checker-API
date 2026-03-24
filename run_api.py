from bibverify_api import create_app

app = create_app()

if __name__ == '__main__':
    import os
    import uvicorn
    host = os.environ.get('BIBVERIFY_HOST', '0.0.0.0')
    port = int(os.environ.get('BIBVERIFY_PORT', '8000'))
    uvicorn.run('run_api:app', host=host, port=port, reload=False)
