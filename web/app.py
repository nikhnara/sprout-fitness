"""Dedicated HTTPS origin serving public UI assets from a private GCS bucket."""
import mimetypes
import os
from flask import Flask, Response, abort
from google.cloud import storage
from google.api_core.exceptions import NotFound
app = Flask(__name__)
bucket = storage.Client().bucket(os.environ['UI_BUCKET'])

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/', defaults={'path': 'index.html'})
@app.get('/<path:path>')
def asset(path):
    if any(part.startswith('.') for part in path.split('/')) or '\\' in path:
        abort(404)
    try:
        data = bucket.blob(path).download_as_bytes(timeout=30)
    except NotFound:
        abort(404)
    mime = 'text/javascript' if path.endswith('.mjs') else mimetypes.guess_type(path)[0]
    response = Response(data, content_type=mime or 'application/octet-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response
