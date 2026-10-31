"""Disposable owned-loopback fixture. No real provider, account data or .env loader."""
import argparse,json,os,secrets,socket,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--lightweight-game',action='store_true',help='Functional studio UI only; never a performance/gameplay verdict')
parser.add_argument('--included-beta',action='store_true',help='Synthetic included/BYOK provider; requires lightweight game and never calls a provider')
args=parser.parse_args()
if args.included_beta and not args.lightweight_game:parser.error('--included-beta requires --lightweight-game')
with tempfile.TemporaryDirectory(prefix='openworld-ui-') as temporary:
    root=Path(temporary);os.chmod(root,0o700)
    safe={'HOME':os.environ.get('HOME','/Users/nirfeinstein'),'PATH':'/usr/bin:/bin:/usr/local/bin','TMPDIR':'/tmp','LANG':'C','DATA_DIR':str(root/'data'),'VERSIONS_DIR':str(root/'versions'),'JWT_SECRET':'synthetic-fixture-secret-at-least-32-characters','SEED_DEMO_STORE':'0'}
    if args.lightweight_game:
        base=root/'functional-game.html';base.write_text('<!doctype html><html lang="en"><title>Synthetic game fixture</title><body style="background:#182435;color:#fff;font:18px system-ui"><h1>Functional studio fixture</h1><p>Account and editor UI only. This is not a game or performance measurement.</p></body></html>');safe['BASE_GAME_PATH']=str(base)
    os.environ.clear();os.environ.update(safe);sys.path.insert(0,str(ROOT));os.chdir(ROOT)
    from app.backend.database import init_db,SessionLocal
    from app.backend.models import User,ChatSession,ChatMessage,GameVersion,ContactMessage
    from app.backend.auth import hash_password
    from app.backend.main import app
    if args.included_beta:
        import re
        from types import SimpleNamespace
        from app.backend import included_ai,agent
        def synthetic_generate(system,messages,**kwargs):
            text=messages[-1]['content']
            if not isinstance(text,str):text='\n'.join(x.get('text','') for x in text if x.get('type')=='text')
            if 'User request: fixture unknown' in text:raise included_ai.IncludedError('outcome_unknown','The creation result is uncertain. Check saved versions; this reference will not be sent again.')
            code=re.search(r'<current_game_code>\n(.*?)\n</current_game_code>',text,re.S).group(1)
            replacement=code.replace('</body>','<p>Claude created a small blue zone.</p></body>')
            return SimpleNamespace(stop_reason='end_turn',content=[SimpleNamespace(type='text',text='<<<SEARCH\n'+code+'\n===\n'+replacement+'\n>>>SEARCH\n<description>A small blue zone appeared.</description><suggestions>[]</suggestions>')])
        included_ai.ready=lambda:True
        included_ai.generate=synthetic_generate
        class SyntheticClient:
            def __init__(self,**kwargs):self.messages=SimpleNamespace(create=lambda **body:synthetic_generate(body['system'],body['messages']))
        agent.anthropic.Anthropic=SyntheticClient
    init_db();accounts=[]
    with SessionLocal() as db:
        for width in [375,1440]:
            password=secrets.token_urlsafe(24);username='ui'+str(width)+secrets.token_hex(4);email=username+'@example.invalid'
            user=User(username=username,email=email,password_hash=hash_password(password));db.add(user);db.flush()
            session=ChatSession(user_id=user.id);db.add(session);db.flush()
            db.add(ChatMessage(session_id=session.id,role='user',content='Synthetic owned chat '+str(width)))
            filename=secrets.token_hex(16)+'.html';(root/'versions'/filename).write_text('<!doctype html><html lang="en"><title>Owned game</title><body>OWNED_SYNTHETIC_GAME_'+str(width)+'</body></html>')
            version=GameVersion(user_id=user.id,session_id=session.id,version_number=1,description='Synthetic owned game '+str(width),file_path=filename,is_suggested=True,suggestion_status='pending');db.add(version);db.flush()
            accounts.append({'width':width,'username':username,'email':email,'password':password,'versionId':version.id,'sessionId':session.id})
        other=User(username='other'+secrets.token_hex(5),email='other'+secrets.token_hex(5)+'@example.invalid',password_hash=hash_password(secrets.token_urlsafe(24)))
        db.add(other);db.flush()
        private_session=ChatSession(user_id=other.id);db.add(private_session);db.flush()
        private_name=secrets.token_hex(16)+'.html';(root/'versions'/private_name).write_text('<!doctype html><html>UNSUBMITTED_PRIVATE_GAME</html>')
        db.add(GameVersion(user_id=other.id,session_id=private_session.id,version_number=1,description='Private unsubmitted game',file_path=private_name))
        admin_password=secrets.token_urlsafe(24);admin_username='admin'+secrets.token_hex(5)
        db.add(User(username=admin_username,email=admin_username+'@example.invalid',password_hash=hash_password(admin_password),is_admin=True))
        for width in [375,1440]:db.add(ContactMessage(name='Synthetic contact '+str(width),email='contact'+str(width)+'@example.invalid',message='Synthetic admin-only message '+str(width)))
        db.commit()
    sock=socket.socket();sock.bind(('127.0.0.1',0));sock.listen()
    base='http://127.0.0.1:'+str(sock.getsockname()[1]);fixture=root/'fixture.json';fixture.write_text(json.dumps({'synthetic':True,'scope':'functional studio UI' if args.lightweight_game else 'real base game','base':base,'accounts':accounts,'admin':{'username':admin_username,'password':admin_password}}));os.chmod(fixture,0o600)
    print('Loopback fixture:'+base+' private configuration:'+str(fixture),flush=True)
    import uvicorn
    config=uvicorn.Config(app,host='127.0.0.1',port=sock.getsockname()[1],log_level='warning',access_log=False)
    try:uvicorn.Server(config).run(sockets=[sock])
    except KeyboardInterrupt:pass
    finally:sock.close()
