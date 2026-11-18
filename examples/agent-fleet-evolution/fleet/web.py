"""Loopback-only read-only visualization; actual SDK data, no fixture fallback."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from functools import lru_cache
from pathlib import Path
import json
from .demo import read
ROOT=Path(__file__).resolve().parents[1]/'web'
def serve(config,run,port):
 @lru_cache(maxsize=1)
 def snapshot():return read(config,run)
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def response(self,status,raw,mime):
   self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Content-Security-Policy',"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'");self.end_headers()
   if self.command!='HEAD':self.wfile.write(raw)
  def do_GET(self):
   hosts={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
   if self.headers.get('Host') not in hosts or self.headers.get('Origin') not in {None,*(('http://'+h) for h in hosts)}:return self.response(403,b'Use the local origin','text/plain')
   if self.path=='/api/run':
    try:return self.response(200,json.dumps(snapshot(),ensure_ascii=False).encode(),'application/json')
    except Exception:return self.response(503,b'{"error":"Scoped persisted data unavailable; no fixture fallback"}','application/json')
   assets={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
   if self.path not in assets:return self.response(404,b'Not found','text/plain')
   name,mime=assets[self.path];return self.response(200,(ROOT/name).read_bytes(),mime+'; charset=utf-8')
  do_HEAD=do_GET
  def reject(self):self.response(405,b'Read only','text/plain')
  do_POST=do_PUT=do_PATCH=do_DELETE=do_OPTIONS=do_CONNECT=do_TRACE=reject
 with ThreadingHTTPServer(('127.0.0.1',port),Handler) as server:
  print(f'Public fleet dashboard http://127.0.0.1:{server.server_port}/',flush=True)
  try:server.serve_forever()
  except KeyboardInterrupt:pass
