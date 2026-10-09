"""Local UI review server with an explicit fake session; never shipped to dist."""
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]/'dist'
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT),**kw)
 def do_GET(self):
  if self.path=='/firebase-session.mjs':
   body="""export async function createFirebaseSession(config,onChange){const user={uid:'local-review-only',email:'review@example.test',displayName:'Review User'};setTimeout(()=>onChange(null),0);return {signIn:async()=>onChange(user),signOut:async()=>onChange(null),idToken:async()=>'local-review'};}""";self.send_response(200);self.send_header('Content-Type','text/javascript');self.end_headers();self.wfile.write(body.encode());return
  if self.path=='/config.js':
   self.send_response(200);self.send_header('Content-Type','text/javascript');self.end_headers();self.wfile.write(b'window.SPROUT_CONFIG={apiUrl:"/mock",firebase:{apiKey:"local-review"}};');return
  if self.path.startswith('/mock/'):
   self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'state':None,'revision':0,'items':[]}).encode());return
  return super().do_GET()
 def do_POST(self):
  data=json.loads(self.rfile.read(int(self.headers.get('Content-Length',0))));self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(json.dumps({'revision':data.get('baseRevision',0)+1,'status':'saved'}).encode())
if __name__=='__main__': ThreadingHTTPServer(('127.0.0.1',5174),Handler).serve_forever()
