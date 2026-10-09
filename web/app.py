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
    if path in ('assets/nikhil-avatar.png','assets/companion.png'): abort(404)
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

@app.after_request
def secure_headers(response):
    response.headers['X-Frame-Options']='DENY'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' https://www.gstatic.com https://apis.google.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https://images.openfoodfacts.org; connect-src 'self' https://*.run.app https://*.googleapis.com https://*.firebaseapp.com https://www.gstatic.com; frame-src https://*.firebaseapp.com https://accounts.google.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
    return response
