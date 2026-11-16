import json
from pathlib import Path
import httpx
base='http://127.0.0.1:8000'
with httpx.Client(timeout=120) as c:
    assert c.get(base+'/health').status_code==200
    token=c.post(base+'/sessions').json()['token']
    c.headers['Authorization']='Bearer '+token
    offers=c.get(base+'/catalog').json()
    candidates=[o for o in offers if o['stock_status']=='in_stock' and not o['is_demo']]
    assert candidates,'Collect real offers first'
    offer=min(candidates,key=lambda o:float(o['price_tnd']))
    r=c.post(base+'/structured-request',json={'email':'demo@example.com','requirements':{'category':offer['category'],'quantity':1,'budget':'10000'}})
    r.raise_for_status(); state=r.json(); assert state['status']=='awaiting_approval',state
    p=state['proposal']; path=base+'/runs/'+state['thread_id']+'/approval'
    decision={'proposal_id':p['id'],'proposal_hash':p['hash'],'approve':True}
    result=c.post(path,json=decision); result.raise_for_status(); result=result.json()
    assert result['status']=='success',result
    duplicate=c.post(path,json=decision).json()
    assert duplicate['order']['id']==result['order']['id']
    assert len(c.get(base+'/orders').json())==1
    summary={'mode':'manual structured request; real scraped catalog','status':result['status'],'steps':result['steps'],
        'order':result['order'],'email_result':result.get('email_result'),'thread_id':state['thread_id'],
        'duplicate_confirm_created_second_order':False}
    Path('data/smoke-demo.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
