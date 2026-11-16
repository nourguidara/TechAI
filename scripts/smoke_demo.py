"""Isolated synthetic demonstration: never connects to configured Gmail or the running API."""
import json,os,socket,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); os.chdir(ROOT)
work=Path(tempfile.mkdtemp(prefix='recommendation-demo-',dir=ROOT/'data'))
with socket.socket() as sock:
    sock.bind(('127.0.0.1',0)); port=sock.getsockname()[1]
os.environ.update(DATABASE_URL='sqlite:///'+(work/'demo.db').as_posix(),EMAIL_MODE='sandbox',
    SMTP_HOST='127.0.0.1',SMTP_PORT=str(port),LANGSMITH_TRACING='false')
from aiosmtpd.controller import Controller
from fastapi.testclient import TestClient
from backend.database import init_db
from backend.main import app
from sandbox.seed import seed
from sandbox.recommendation_fixtures import seed_variants
class Capture:
    messages=[]
    async def handle_DATA(self,server,session,envelope):
        self.messages.append(envelope.content); return '250 captured locally'
init_db(); seed(); seed_variants()
capture=Capture(); smtp=Controller(capture,hostname='127.0.0.1',port=port); smtp.start()
try:
    with TestClient(app) as c:
        headers={'Authorization':'Bearer '+c.post('/sessions').json()['token']}
        s=c.post('/structured-request',headers=headers,json={'email':'demo@example.com','requirements':{
            'category':'laptop','budget':'5000','intended_use':['programming']}}).json()
        assert s['status']=='awaiting_selection' and not c.get('/orders',headers=headers).json()
        recommendations=s['comparison']; path='/runs/'+s['thread_id']
        chosen=recommendations[1]
        s=c.post(path+'/selection',headers=headers,json={'selection_id':s['selection']['id'],
            'offer_id':chosen['id'],'quantity':2}).json()
        assert s['status']=='awaiting_approval' and not c.get('/orders',headers=headers).json()
        proposal=s['proposal']; decision={'proposal_id':proposal['id'],'proposal_hash':proposal['hash'],'approve':True}
        result=c.post(path+'/approval',headers=headers,json=decision).json()
        assert result['status']=='success' and result['email_result']['status']=='sent'
        duplicate=c.post(path+'/approval',headers=headers,json=decision).json()
        assert duplicate['order']['id']==result['order']['id']
        assert len(c.get('/orders',headers=headers).json())==len(capture.messages)==1
        summary={'mode':'Synthetic fixtures; isolated database; actual loopback SMTP; no OpenAI or external email',
            'status':result['status'],'steps':result['steps'],'recommendations':recommendations,
            'selected_offer_id':chosen['id'],'quantity':2,'order_count':1,'captured_email_count':1,
            'selection_created_order':False,'duplicate_created_order':False}
        Path('data/smoke-demo.json').write_text(json.dumps(summary,indent=2))
        print(json.dumps({k:v for k,v in summary.items() if k!='recommendations'},indent=2))
finally: smtp.stop()
