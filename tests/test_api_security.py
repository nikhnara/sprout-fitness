"""API integration tests using Flask and isolated in-memory cloud adapters."""
import copy,importlib,os,sys,time,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
sys.path.insert(0,str(Path(__file__).parents[1]/'server'))
from test_validation import valid
class Snapshot:
 def __init__(self,ref): self.reference=ref;self.id=ref.path.split('/')[-1];self.exists=ref.path in ref.db.rows;self.data=copy.deepcopy(ref.db.rows.get(ref.path))
 def to_dict(self): return copy.deepcopy(self.data)
class Ref:
 def __init__(self,db,path):self.db=db;self.path=path
 def collection(self,key):return Collection(self.db,self.path+'/'+key)
 def get(self,transaction=None):return Snapshot(self)
 def set(self,data,merge=False):self.db.rows[self.path]={**(self.db.rows.get(self.path,{}) if merge else {}),**copy.deepcopy(data)}
 def update(self,data):self.set(data,True)
class Collection:
 def __init__(self,db,path):self.db=db;self.path=path;self.condition=None;self.maximum=100
 def document(self,key):return Ref(self.db,self.path+'/'+key)
 def where(self,key,op,val):self.condition=(key,val);return self
 def limit(self,n):self.maximum=n;return self
 def stream(self):
  result=[]
  for path,value in list(self.db.rows.items()):
   if path.startswith(self.path+'/') and path.count('/')==self.path.count('/')+1 and (not self.condition or value.get(self.condition[0])==self.condition[1]):result.append(Snapshot(Ref(self.db,path)))
  return iter(result[:self.maximum])
class Tx:
 def set(self,ref,data,merge=False):ref.set(data,merge)
 def delete(self,ref):ref.db.rows.pop(ref.path,None)
 def commit(self):pass
class DB:
 def __init__(self):self.rows={}
 def collection(self,key):return Collection(self,key)
 def transaction(self):return Tx()
 def batch(self):return Tx()
class APISecurity(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import firebase_admin
  from google.cloud import firestore,bigquery
  cls.patches=[patch.dict(os.environ,{'GOOGLE_CLOUD_PROJECT':'test-project','FIREBASE_PROJECT_ID':'test-auth','AUTH_MODE':'multi','ALLOWED_ORIGINS':'https://gamna.app'}),patch.object(firebase_admin,'initialize_app'),patch.object(firestore,'Client',return_value=DB()),patch.object(firestore,'transactional',side_effect=lambda f:f),patch.object(bigquery,'Client',return_value=MagicMock())]
  for p in cls.patches:p.start()
  cls.api=importlib.import_module('app');cls.client=cls.api.app.test_client()
 @classmethod
 def tearDownClass(cls):
  for p in reversed(cls.patches):p.stop()
 def setUp(self):
  self.api.db.rows.clear();self.api.bq.reset_mock();self.api.bq.insert_rows_json.return_value=[]
  def verify(token):
   if token not in ['alice','bob']:raise ValueError('bad token')
   return {'uid':token,'email':token+'@example.test','email_verified':True,'firebase':{'sign_in_provider':'google.com'}}
  self.verifier=patch.object(self.api.firebase_auth,'verify_id_token',side_effect=verify);self.verifier.start()
 def tearDown(self):self.verifier.stop()
 def headers(self,user='alice'):return {'Authorization':'Bearer '+user,'Origin':'https://gamna.app'}
 def post(self,path,data,user='alice'):return self.client.post(path,json=data,headers=self.headers(user))
 def test_no_auth_and_forged_tokens_cannot_read_or_write(self):
  for path in ['/state','/profile','/imports','/connections']:
   self.assertEqual(self.client.get(path).status_code,401)
   self.assertEqual(self.client.get(path,headers=self.headers('forged')).status_code,401)
  self.assertEqual(self.post('/sync',{},'forged').status_code,401)
 def test_user_isolation_and_analytics_identity(self):
  body={'eventId':'event-1234567890123456','baseRevision':0,'state':valid()}
  self.assertEqual(self.post('/sync',body).status_code,200)
  self.assertIsNone(self.client.get('/state?owner=alice',headers=self.headers('bob')).json['state'])
  self.assertEqual(self.client.get('/state',headers=self.headers()).json['revision'],1)
  row=self.api.bq.insert_rows_json.call_args[0][1][0]
  import hashlib
  self.assertEqual(row['owner_id'],hashlib.sha256(b'alice').hexdigest())
  self.assertIsInstance(row['payload'],str)
 def test_revision_conflict_and_idempotency(self):
  b={'eventId':'event-1234567890123456','baseRevision':0,'state':valid()}
  self.assertEqual(self.post('/sync',b).status_code,200)
  self.assertEqual(self.post('/sync',b).json['revision'],1)
  self.assertEqual(self.post('/sync',{**b,'eventId':'different-1234567890'}).status_code,409)
  b['state']['profile']['name']='Changed'
  self.assertEqual(self.post('/sync',b).status_code,409)
 def test_unsafe_origin_is_rejected(self):
  self.assertEqual(self.client.get('/state',headers={'Origin':'https://evil.test','Authorization':'Bearer alice'}).status_code,403)
 def test_unsafe_links_and_malformed_state_rejected(self):
  s=valid();s['customFoods']=[{'sourceUrl':'javascript:alert(1)'}]
  self.assertEqual(self.post('/sync',{'eventId':'event-1234567890123456','baseRevision':0,'state':s}).status_code,400)
  s=valid();s['days']['2026-10-07']=[]
  self.assertEqual(self.post('/sync',{'eventId':'event-1234567890123456','baseRevision':0,'state':s}).status_code,400)
 def test_connection_is_upload_only_scoped_and_revocable(self):
  key=self.post('/connections',{'action':'create'}).json['token'];header={'Authorization':'Bearer '+key}
  self.assertEqual(self.client.get('/state',headers=header).status_code,401)
  data={'date':'2026-10-09','sourceId':'sample-1','minutes':20,'name':'Walking'}
  self.assertEqual(self.client.post('/activity',json=data,headers=header).status_code,202)
  self.assertEqual(self.client.post('/activity',json=data,headers=header).status_code,202)
  self.assertEqual(len(self.client.get('/imports',headers=self.headers()).json['items']),1)
  self.assertEqual(self.client.get('/imports',headers=self.headers('bob')).json['items'],[])
  self.assertEqual(self.client.post('/activity',json={**data,'minutes':21},headers=header).status_code,409)
  self.post('/profile',{'photo':None})
  self.post('/connections',{'action':'revoke'})
  self.assertEqual(self.client.post('/activity',json=data,headers=header).status_code,401)
 def test_profile_photo_validation_and_isolation(self):
  import base64
  import io
  from PIL import Image
  raw=io.BytesIO();Image.new('RGB',(2,2)).save(raw,format='JPEG')
  photo='data:image/jpeg;base64,'+base64.b64encode(raw.getvalue()).decode()
  self.assertEqual(self.post('/profile',{'photo':photo}).status_code,200)
  self.assertIsNone(self.client.get('/profile',headers=self.headers('bob')).json['photo'])
  self.assertEqual(self.post('/profile',{'photo':'data:image/svg+xml,<svg onload="alert(1)"/>'}).status_code,400)
 def test_write_rate_limit(self):
  for _ in range(60):self.assertEqual(self.post('/profile',{'photo':None}).status_code,200)
  self.assertEqual(self.post('/profile',{'photo':None}).status_code,429)
 def test_failed_analytics_write_keeps_diary_and_outbox(self):
  self.api.bq.insert_rows_json.return_value=[{'error':'unavailable'}]
  response=self.post('/sync',{'eventId':'event-1234567890123456','baseRevision':0,'state':valid()})
  self.assertEqual(response.status_code,503);self.assertEqual(response.json['acceptedRevision'],1)
  self.assertEqual(self.client.get('/state',headers=self.headers()).json['revision'],1)
  self.api.bq.insert_rows_json.return_value=[]
  self.assertEqual(self.post('/sync',{'eventId':'event-1234567890123456','baseRevision':0,'state':valid()}).status_code,200)

 def test_portion_markup_cannot_be_stored(self):
  s=valid();s['customFoods']=[{'id':'custom-1','name':'Attack','nutrients':{},'portions':[{'label':'cup','grams':'" onmouseover=alert(1)'}]}]
  self.assertEqual(self.post('/sync',{'eventId':'event-1234567890123456','baseRevision':0,'state':s}).status_code,400)

 def test_malformed_connection_requests_fail_cleanly(self):
  self.assertEqual(self.post('/connections',['unexpected']).status_code,400)
  self.assertEqual(self.post('/imports/ack',['unexpected']).status_code,400)

 def test_login_metadata_is_pseudonymous_and_same_session_is_not_reexported(self):
  claims={'uid':'alice','email':'alice@example.test','email_verified':True,'auth_time':1791540000,'firebase':{'sign_in_provider':'google.com'}}
  with patch.object(self.api.firebase_auth,'verify_id_token',return_value=claims):
   self.assertEqual(self.client.get('/state',headers=self.headers()).status_code,200)
   self.assertEqual(self.client.get('/state',headers=self.headers()).status_code,200)
  self.assertEqual(self.api.bq.insert_rows_json.call_count,1)
  table,rows=self.api.bq.insert_rows_json.call_args.args
  self.assertTrue(table.endswith('.login_events'))
  self.assertEqual(set(rows[0]),{'event_id','owner_id','auth_project','signed_in_at','observed_at'})
  self.assertNotIn('alice',str(rows))

 def test_login_metadata_failure_does_not_block_diary_and_retries(self):
  claims={'uid':'alice','email':'alice@example.test','email_verified':True,'auth_time':1791540000,'firebase':{'sign_in_provider':'google.com'}}
  self.api.bq.insert_rows_json.return_value=[{'error':'unavailable'}]
  with patch.object(self.api.firebase_auth,'verify_id_token',return_value=claims):
   self.assertEqual(self.client.get('/state',headers=self.headers()).status_code,200)
   self.api.bq.insert_rows_json.return_value=[]
   self.assertEqual(self.client.get('/state',headers=self.headers()).status_code,200)
  self.assertEqual(self.api.bq.insert_rows_json.call_count,2)
