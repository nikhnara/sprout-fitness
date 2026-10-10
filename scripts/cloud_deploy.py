"""Cloud Build release entrypoint. Uses the build's short-lived service identity."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


def config(env):
    required = ['PROJECT_ID', 'REGION', 'BUCKET_NAME', 'OWNER_EMAIL',
                'FIREBASE_CONFIG', 'FRONTEND_ORIGIN', 'IMAGE_URI', 'DEPLOY_BRANCH']
    c = {k: env.get(k, '').strip() for k in required}
    missing = [key for key, value in c.items() if not value]
    if missing:
        names = {'REGION': '_REGION', 'BUCKET_NAME': '_BUCKET_NAME', 'OWNER_EMAIL': '_OWNER_EMAIL',
                 'FIREBASE_CONFIG': '_FIREBASE_CONFIG', 'FRONTEND_ORIGIN': '_FRONTEND_ORIGIN',
                 'DEPLOY_BRANCH': 'BRANCH_NAME (run the main-branch trigger)'}
        raise ValueError('Missing deployment settings: ' + ', '.join(names.get(key, key) for key in missing))
    if c['DEPLOY_BRANCH'] != 'main':
        raise ValueError('Production deployment is restricted to main.')
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', c['PROJECT_ID']):
        raise ValueError('Invalid Google Cloud project ID.')
    if not re.fullmatch(r'[a-z]+-[a-z]+[0-9]', c['REGION']):
        raise ValueError('Invalid region.')
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{1,220}[a-z0-9]', c['BUCKET_NAME']):
        raise ValueError('Invalid bucket name.')
    origin = urlparse(c['FRONTEND_ORIGIN'])
    if origin.scheme != 'https' or not origin.hostname or origin.path or origin.query or origin.fragment or origin.username:
        raise ValueError('FRONTEND_ORIGIN must be an HTTPS origin without a path or trailing slash.')
    if origin.hostname in ('storage.googleapis.com', 'storage.cloud.google.com'):
        raise ValueError('Use a dedicated HTTPS frontend origin for Google sign-in, not the shared GCS object origin.')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', c['OWNER_EMAIL']):
        raise ValueError('Invalid owner email.')
    try:
        firebase = json.loads(c['FIREBASE_CONFIG'])
    except (ValueError, TypeError):
        raise ValueError('FIREBASE_CONFIG must be the Firebase web configuration JSON.')
    allowed = {'apiKey', 'authDomain', 'projectId', 'appId', 'storageBucket', 'messagingSenderId', 'measurementId', 'databaseURL'}
    if not isinstance(firebase, dict) or not set(firebase).issubset(allowed):
        raise ValueError('Use only the public Firebase web configuration; no credentials.')
    for field in ['apiKey', 'authDomain', 'projectId', 'appId']:
        if not isinstance(firebase.get(field), str) or not firebase[field].strip():
            raise ValueError('Firebase web config is missing ' + field)
    if not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', firebase['projectId']):
        raise ValueError('Invalid Firebase project ID.')
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', firebase['authDomain']):
        raise ValueError('Firebase authDomain must be a hostname.')
    c['firebase'] = firebase
    expected = f"{c['REGION']}-docker.pkg.dev/{c['PROJECT_ID']}/sprout/api:"
    if not c['IMAGE_URI'].startswith(expected) or not re.fullmatch(r'[a-f0-9]{40}', c['IMAGE_URI'][len(expected):]):
        raise ValueError('Image must be tagged with the source commit in this project.')
    return c


def run(*args):
    try:
        return subprocess.check_output(args, text=True).strip()
    except subprocess.CalledProcessError as e:
        if e.output: print(e.output, file=sys.stderr)
        raise


def deploy(c):
    run(sys.executable, 'scripts/migrate_catalog.py', '--project', c['PROJECT_ID'])
    settings = {'AUTH_MODE': 'multi', 'GOOGLE_CLOUD_PROJECT': c['PROJECT_ID'], 'OWNER_EMAIL': c['OWNER_EMAIL'],
                'ALLOWED_ORIGINS': c['FRONTEND_ORIGIN'], 'FIREBASE_PROJECT_ID': c['firebase']['projectId'],
                'BIGQUERY_TABLE': c['PROJECT_ID'] + '.fitness.events'}
    with tempfile.TemporaryDirectory() as directory:
        env_file = Path(directory) / 'runtime.json'
        env_file.write_text(json.dumps(settings))
        run('gcloud', 'run', 'deploy', 'sprout-api', '--image', c['IMAGE_URI'],
            '--project', c['PROJECT_ID'], '--region', c['REGION'],
            '--service-account', f"gamna-396@{c['PROJECT_ID']}.iam.gserviceaccount.com",
            '--env-vars-file', str(env_file), '--allow-unauthenticated',
            '--max-instances', '2', '--memory', '512Mi', '--quiet')
    api = run('gcloud', 'run', 'services', 'describe', 'sprout-api', '--project', c['PROJECT_ID'],
              '--region', c['REGION'], '--format=value(status.url)')
    if not api.startswith('https://'):
        raise ValueError('Cloud Run did not return a valid HTTPS URL.')
    Path('dist/config.js').write_text('window.SPROUT_CONFIG = ' + json.dumps({
        'apiUrl': api, 'firebase': c['firebase']}) + ';\n')
    # Upload the entry point last. Assets use no-cache until content hashing is introduced.
    bucket = 'gs://' + c['BUCKET_NAME']
    run('gcloud', 'storage', 'rsync', 'dist', bucket, '--recursive',
        r'--exclude=^index\.html$', '--cache-control=no-cache', '--project', c['PROJECT_ID'])
    run('gcloud', 'storage', 'cp', 'dist/index.html', bucket + '/index.html',
        '--cache-control=no-cache', '--project', c['PROJECT_ID'])
    web_image = c['IMAGE_URI'].replace('/sprout/api:', '/sprout/web:')
    run('gcloud', 'run', 'deploy', 'sprout-web', '--image', web_image,
        '--project', c['PROJECT_ID'], '--region', c['REGION'],
        '--service-account', f"sprout-web@{c['PROJECT_ID']}.iam.gserviceaccount.com",
        '--set-env-vars', 'UI_BUCKET=' + c['BUCKET_NAME'], '--allow-unauthenticated',
        '--max-instances', '2', '--memory', '512Mi', '--quiet')
    print('Deployed commit image:', c['IMAGE_URI'])
    print('Frontend:', c['FRONTEND_ORIGIN'])


if __name__ == '__main__':
    settings = config(os.environ)
    if sys.argv[1:] == ['deploy']:
        deploy(settings)
    elif sys.argv[1:] == ['validate']:
        print('Deployment configuration validated.')
    else:
        raise SystemExit('Usage: cloud_deploy.py validate|deploy')
