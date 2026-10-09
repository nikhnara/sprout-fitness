"""User-isolated authenticated diary API; Firestore snapshots and BigQuery JSON audit events."""
import datetime, hashlib, json, os, re, secrets, time, base64, io
from PIL import Image
Image.MAX_IMAGE_PIXELS=1_000_000
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
AUTH_MODE=os.environ.get('AUTH_MODE','single')
if AUTH_MODE not in ('single','multi'): raise RuntimeError('Invalid authentication mode.')
OWNER=os.environ.get('OWNER_EMAIL','').lower() if AUTH_MODE=='single' else ''
if AUTH_MODE=='single' and not OWNER: raise RuntimeError('Owner account is required in single-user mode.')
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
    if request.path == '/activity' and request.method == 'POST':
        return authenticate_connection()
    try:
        request.claims={}
        def verify(token):
            claims=firebase_auth.verify_id_token(token)
            request.claims=claims
            return claims
        request.owner=owner_from_bearer(request.headers.get('Authorization'), OWNER, verify)
    except Exception: return jsonify(error='Please sign in to continue.'),401

@app.before_request
def limit_writes():
    if request.method != 'POST' or not hasattr(request, 'owner'): return None
    ref=db.collection('requestLimits').document(request.owner)
    minute=int(time.time()//60)
    @firestore.transactional
    def consume(tx):
        row=ref.get(transaction=tx).to_dict() or {}
        count=row.get('count',0) if row.get('minute')==minute else 0
        if count>=60: return False
        tx.set(ref,{'minute':minute,'count':count+1})
        return True
    if not consume(db.transaction()): return jsonify(error='Please wait a minute before trying again.'),429

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
    return jsonify(state=value.get('state'),revision=value.get('revision',0),legacyEligible=request.claims.get('email','').casefold()==os.environ.get('OWNER_EMAIL','').casefold())

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
        if revision!=current_revision: raise ValueError('Your diary changed on another device. Review the saved copy before continuing.')
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
            return jsonify(error='Your diary is saved. History processing is catching up.',acceptedRevision=record['revision']),503
    except Exception:
        app.logger.exception('BigQuery export failed')
        return jsonify(error='Your diary is saved. History processing will retry shortly.',acceptedRevision=record['revision']),503
    return jsonify(revision=record['revision'],status='synced')

@app.errorhandler(413)
def too_large(e): return jsonify(error='Diary is too large for a single sync. Export your diary for backup.'),413


def authenticate_connection():
    header=request.headers.get('Authorization','')
    if not re.fullmatch(r'Bearer gm_[A-Za-z0-9_-]{43}',header):
        return jsonify(error='Invalid connection key.'),401
    digest=hashlib.sha256(header[7:].encode()).hexdigest()
    record=db.collection('connections').document(digest).get().to_dict() or {}
    if not record.get('active') or record.get('expires',0)<time.time():
        return jsonify(error='Connection expired or revoked.'),401
    request.owner=record['owner']

@app.route('/profile',methods=['GET','POST'])
def profile():
    ref=db.collection('profiles').document(request.owner)
    if request.method=='GET': return jsonify(photo=(ref.get().to_dict() or {}).get('photo'))
    data=request.get_json(silent=True)
    photo=data.get('photo') if isinstance(data,dict) else False
    if photo is not None:
        if not isinstance(photo,str) or not photo.startswith('data:image/jpeg;base64,') or len(photo)>100000:
            return jsonify(error='Choose a smaller JPEG photo.'),400
        try:
            raw=base64.b64decode(photo.split(',')[1],validate=True)
            if not raw.startswith(b'\xff\xd8\xff'): raise ValueError()
            img=Image.open(io.BytesIO(raw))
            if img.format!='JPEG' or max(img.size)>512: raise ValueError()
            img.load()
            clean=io.BytesIO();img.convert('RGB').save(clean,format='JPEG',quality=85)
            photo='data:image/jpeg;base64,'+base64.b64encode(clean.getvalue()).decode()
        except Exception: return jsonify(error='Invalid photo.'),400
    ref.set({'photo':photo},merge=True)
    return jsonify(status='saved')

@app.route('/connections',methods=['GET','POST'])
def connections():
    ref=db.collection('profiles').document(request.owner)
    profile=ref.get().to_dict() or {}
    if request.method=='GET':
        return jsonify(active=bool(profile.get('connection')),expires=profile.get('connectionExpires',0))
    data=request.get_json(silent=True) or {}
    if not isinstance(data,dict) or data.get('action') not in ['create','revoke']: return jsonify(error='Invalid action.'),400
    token='gm_'+secrets.token_urlsafe(32)
    digest=hashlib.sha256(token.encode()).hexdigest()
    expires=int(time.time())+14*86400
    @firestore.transactional
    def rotate(tx):
        current=ref.get(transaction=tx).to_dict() or {}
        if current.get('connection'): tx.delete(db.collection('connections').document(current['connection']))
        if data['action']=='revoke':
            tx.set(ref,{'connection':None,'connectionExpires':0},merge=True)
        else:
            tx.set(db.collection('connections').document(digest),{'owner':request.owner,'active':True,'expires':expires})
            tx.set(ref,{'connection':digest,'connectionExpires':expires},merge=True)
    rotate(db.transaction())
    if data['action']=='revoke':return jsonify(active=False)
    return jsonify(token=token,expires=expires)

@app.post('/activity')
def receive_activity():
    from validation import validate_activity
    try: data=validate_activity(request.get_json(silent=True))
    except (ValueError,TypeError): return jsonify(error='Use a valid date, sourceId and activity measurements.'),400
    ref=db.collection('diaries').document(request.owner).collection('imports').document(hashlib.sha256(data['sourceId'].encode()).hexdigest())
    @firestore.transactional
    def save(tx):
        prior=ref.get(transaction=tx)
        if prior.exists:
            if prior.to_dict().get('data')!=data: return False
            return True
        tx.set(ref,{'data':data,'reviewed':False,'received':int(time.time())})
        return True
    if not save(db.transaction()): return jsonify(error='This sourceId already has different measurements.'),409
    return jsonify(status='pending_review'),202

@app.get('/imports')
def imports():
    records=db.collection('diaries').document(request.owner).collection('imports').where('reviewed','==',False).limit(30).stream()
    return jsonify(items=[{'id':r.id,**r.to_dict()['data']} for r in records])

@app.post('/imports/ack')
def acknowledge():
    data=request.get_json(silent=True) or {}
    ids=data.get('ids') if isinstance(data,dict) else None
    if not isinstance(ids,list) or len(ids)>30 or any(not isinstance(x,str) or not re.fullmatch('[a-f0-9]{64}',x) for x in ids):
        return jsonify(error='Invalid import IDs.'),400
    batch=db.batch()
    for id in ids: batch.set(db.collection('diaries').document(request.owner).collection('imports').document(id),{'reviewed':True},merge=True)
    batch.commit()
    return jsonify(status='reviewed')

@app.get('/foods/barcode/<code>')
def barcode(code):
    if not re.fullmatch(r'\d{8,14}',code): return jsonify(error='Enter an 8–14 digit product barcode.'),400
    cache=db.collection('foodCache').document(code)
    saved=cache.get().to_dict() or {}
    if saved.get('expires',0)>time.time():return jsonify(food=saved['food'])
    ref=db.collection('requestLimits').document('openfoodfacts')
    @firestore.transactional
    def reserve(tx):
        row=ref.get(transaction=tx).to_dict() or {};minute=int(time.time()//60)
        count=row.get('count',0) if row.get('minute')==minute else 0
        if count>=12:return False
        tx.set(ref,{'minute':minute,'count':count+1});return True
    if not reserve(db.transaction()):return jsonify(error='Product lookup is busy. Please try again in a minute.'),429
    try:
        import requests
        from food_lookup import normalize_product
        response=requests.get('https://world.openfoodfacts.org/api/v3.6/product/'+code,
            params={'fields':'product_name,brands,quantity,nutriments,image_front_small_url,nutrition_data_per'},
            headers={'User-Agent':'Gamna/1.0 (+https://gamna.app)'},timeout=8,allow_redirects=False)
        if response.status_code!=200:return jsonify(error='Product not found. You can enter its label manually.'),404
        food=normalize_product(response.json().get('product'),code)
        cache.set({'food':food,'expires':int(time.time())+86400})
        return jsonify(food=food)
    except ValueError as e:return jsonify(error=str(e)),400
    except Exception:return jsonify(error='Product lookup is unavailable. Try again or enter the label manually.'),503
