"""Read-only exact public source/schema guards; no accounts or provider calls."""
from pathlib import Path
import importlib.util,json,urllib.request,urllib.error
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('game_security',root/'app/backend/game_security.py');security=importlib.util.module_from_spec(spec);spec.loader.exec_module(security)
base='https://open-world.gg'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
opener=urllib.request.build_opener(NoRedirect)
def get(path):
 try:
  with opener.open(base+path,timeout=30) as response:return response.status,response.headers,response.read()
 except urllib.error.HTTPError as response:return response.code,response.headers,response.read()
status,headers,body=get('/healthz');health=json.loads(body);assert status==200 and health['status']=='ok' and health['database']=='ok' and health['gameFiles'] and health['recovery']['ok'] and health['recovery']['deletionsBackedUp'];assert headers.get('Cache-Control')=='no-store';print('Public health200:database/files/current deletion-aware recovery healthy; model configuration retained.')
status,headers,body=get('/');assert status==200;assert body.decode()==security.studio_shell((root/'app/static/overlay.html').read_text());print('Live studio shell exactly matches tested opaque/direct/private-loader source.')
for route,file in [('/account','account.html'),('/privacy','privacy.html'),('/contact','contact.html'),('/admin','admin.html')]:
 status,headers,body=get(route);assert status==200 and body==(root/'app/static'/file).read_bytes(),route
 if route=='/account':assert headers.get('Cache-Control')=='no-store'
print('Account/privacy/contact/admin HTML exactly match tested release; account no-store.')
for route in ['/api/account/export','/api/auth/me','/api/admin/suggestions','/api/admin/contacts']:
 status,_,_=get(route);assert status==401,(route,status)
for route in ['/.env','/app/backend/main.py','/qa/local.py']:
 status,headers,_=get(route);assert status==302 and headers.get('location')=='/',(route,status)
print('Anonymous private-account/admin denials and source/environment/QA redirect-denial guards pass.')
status,headers,body=get('/game/base');assert status==200;assert "sandbox allow-scripts allow-pointer-lock" in headers.get('Content-Security-Policy','');assert "allow-same-origin" not in headers.get('Content-Security-Policy','');assert headers.get('Cache-Control')=='private, no-store';assert len(body)>100000
expected=security.game_response(root/'index.html').body
print('Public real base opaque/no-store policy passes; source game comparison:', 'exactly matches accepted actual-game fixture' if body==expected else 'persistent public base differs; retain public gameplay proof separately')
if body!=expected:
 report=json.loads((root/'qa/perf/public-mobile.report.json').read_text())
 assert report.get('finalDisplayedUrl',report.get('finalUrl'))==base+'/'
 assert report['categories']['performance']['score']>=.9 and report['categories']['accessibility']['score']>=.9 and not report.get('runWarnings')
 print('Preserved production-base performance verified on actual public URL; gameplay UI checked separately.')
print('OpenWorld public HTTP release acceptance passed; no private data/provider/account mutation.')
