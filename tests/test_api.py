from fastapi.testclient import TestClient
from backend.main import app

def test_api_approval_and_isolation():
    with TestClient(app) as c:
        token=c.post('/sessions').json()['token']; headers={'Authorization':'Bearer '+token}
        other={'Authorization':'Bearer '+c.post('/sessions').json()['token']}
        r=c.post('/structured-request',headers=headers,json={'email':'student@example.com','requirements':{'category':'laptop','quantity':2,'budget':'4000'}})
        assert r.status_code==200,r.text
        state=r.json(); assert state['status']=='awaiting_approval'
        p=state['proposal']; path='/runs/'+state['thread_id']+'/approval'
        decision={'proposal_id':p['id'],'proposal_hash':p['hash'],'approve':True}
        assert c.post(path,headers=other,json=decision).status_code==404
        result=c.post(path,headers=headers,json=decision)
        assert result.status_code==200,result.text
        assert result.json()['status']=='success',result.json()
        assert c.post(path,headers=headers,json=decision).json()['order']['id']==result.json()['order']['id']
        assert len(c.get('/orders',headers=headers).json())==1
        assert c.get('/orders',headers=other).json()==[]
        assert c.get('/orders').status_code==401
