"""Single-owner authenticated diary API; Firestore snapshots and BigQuery JSON audit events."""
import datetime, hashlib, json, os, re
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import auth as firebase_auth
from auth_policy import owner_from_bearer
from google.cloud import bigquery, firestore
from validation import validate_state

app=Flask(__name__)
app.config['MAX_CONTENT_LENGTH']=1_000_000
PROJECT=os.environ['GOOGLE_CLOUD_PROJECT']
firebase_admin.initialize_app(options={'projectId': os.environ['FIREBASE_PROJECT_ID']})
OWNER=os.environ['OWNER_EMAIL'].lower()
ORIGINS=set(os.environ['ALLOWED_ORIGINS'].split(','))
TABLE=os.environ.get('BIGQUERY_TABLE',f'{PROJECT}.fitness.events')
bq=bigquery.Client(project=PROJECT)
db=firestore.Client(project=PROJECT)

@app.before_request
def guard():
    if request.path=='/health': return None
    origin=request.headers.get('Origin')
    if origin and origin not in ORIGINS: return jsonify(error='Origin not allowed.'),403
    if request.method=='OPTIONS': return '',204
    try:
        request.owner=owner_from_bearer(request.headers.get('Authorization'), OWNER, firebase_auth.verify_id_token)
    except Exception: return jsonify(error='Sign in with the owner Google account to continue.'),401

@app.after_request
def headers(response):
    origin=request.headers.get('Origin')
    if origin in ORIGINS:
        response.headers['Access-Control-Allow-Origin']=origin
        response.headers['Vary']='Origin'
        response.headers['Access-Control-Allow-Headers']='Authorization,Content-Type'
        response.headers['Access-Control-Allow-Methods']='GET,POST,OPTIONS'
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.get('/health')
def health(): return jsonify(status='ok')

@app.get('/state')
def read_state():
    record=db.collection('diaries').document(request.owner).get()
    value=record.to_dict() if record.exists else {}
    return jsonify(state=value.get('state'),revision=value.get('revision',0))

@app.route('/sync',methods=['POST','OPTIONS'])
def sync():
    data=request.get_json(silent=True)
    try:
        if not isinstance(data,dict): raise ValueError('Expected a JSON object.')
        event=data.get('eventId','')
        if not re.fullmatch(r'[a-zA-Z0-9-]{16,80}',event): raise ValueError('Invalid event identifier.')
        revision=data.get('baseRevision')
        if type(revision) is not int or revision<0: raise ValueError('Invalid revision.')
        state=validate_state(data.get('state'))
    except (ValueError,TypeError,AttributeError) as e: return jsonify(error=str(e)),400
    owner=request.owner
    ref=db.collection('diaries').document(owner)
    outbox=ref.collection('outbox').document(event)
    digest=hashlib.sha256(json.dumps(state,sort_keys=True).encode()).hexdigest()
    @firestore.transactional
    def commit(transaction):
        prior=outbox.get(transaction=transaction)
        current=ref.get(transaction=transaction)
        current_revision=(current.to_dict() or {}).get('revision',0)
        if prior.exists:
            record=prior.to_dict()
            if record['digest']!=digest: raise ValueError('Event ID reused with different content.')
            return record
        if revision!=current_revision: raise ValueError('Cloud diary changed on another device. Export this device’s JSON before restoring the cloud copy.')
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
        record={'event_id':event,'owner_id':owner,'received_at':timestamp,'revision':revision+1,'digest':digest,'payload':json.dumps(state,separators=(',',':')),'exported':False}
        transaction.set(ref,{'state':state,'revision':revision+1,'updated_at':timestamp})
        transaction.set(outbox,record)
        return record
    try: record=commit(db.transaction())
    except ValueError as e: return jsonify(error=str(e)),409
    try:
        # Drain earlier accepted events too, so a failed BigQuery write is retried on the next sync.
        pending=list(ref.collection('outbox').where('exported','==',False).limit(30).stream())
        for item in pending:
            r=item.to_dict()
            row={k:r[k] for k in ['event_id','owner_id','received_at','revision','payload']}
            errors=bq.insert_rows_json(TABLE,[row],row_ids=[r['event_id']])
            if errors: raise RuntimeError('BigQuery rejected a write')
            item.reference.update({'exported':True})
        if not outbox.get().to_dict()['exported']:
            return jsonify(error='Diary saved in cloud; older BigQuery events are still catching up. Sync again.',acceptedRevision=record['revision']),503
    except Exception:
        app.logger.exception('BigQuery export failed')
        return jsonify(error='Diary saved in cloud, but BigQuery export is pending. Retry sync to finish.',acceptedRevision=record['revision']),503
    return jsonify(revision=record['revision'],status='synced')

@app.errorhandler(413)
def too_large(e): return jsonify(error='Diary is too large for a single sync. Export JSON for backup.'),413
