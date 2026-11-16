from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,func
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from backend.main import app
from backend.database import Session
from backend.models import Offer,Proposal,Order,ShoppingSelection,now
from backend.schemas import Requirements,SelectionInput
from backend.services.selection import prepare_selection,select_offer,selected_proposal
from agent.graph import build_graph
from sandbox.recommendation_fixtures import seed_variants


def selection():
    return prepare_selection('owner',Requirements(category='laptop',budget='5000',min_ram=8).model_dump(mode='json'))


def test_selection_is_not_approval_and_proposal_is_idempotent():
    s=selection(); data=SelectionInput(selection_id=s['id'],offer_id=s['recommendations'][0]['id'],quantity=2)
    select_offer('owner',data); select_offer('owner',data)
    p=selected_proposal(s['id'],'owner','student@example.com')
    assert selected_proposal(s['id'],'owner','student@example.com')==p
    with Session() as db:
        assert db.get(Proposal,p['id']).status=='pending'
        assert db.scalar(select(func.count(Order.id)))==0
        assert db.scalar(select(func.count(Proposal.id)))==1
    assert p['total']=='3000.000'

@pytest.mark.parametrize('attack',['foreign_session','foreign_offer','quantity_budget','price','stock','stale','expired','tamper'])
def test_selection_rejects(attack):
    s=selection(); oid=s['recommendations'][0]['id']; owner='owner'; qty=1
    if attack=='foreign_session': owner='attacker'
    if attack=='foreign_offer': oid=2
    if attack=='quantity_budget': qty=4
    with Session.begin() as db:
        o=db.get(Offer,1); record=db.get(ShoppingSelection,s['id'])
        if attack=='price': o.price_tnd=Decimal('1501')
        if attack=='stock': o.stock_status='out_of_stock'
        if attack=='stale': o.scraped_at=now()-timedelta(days=10)
        if attack=='expired': record.expires_at=now()-timedelta(seconds=1)
        if attack=='tamper': record.payload={**record.payload,'requirements':{'budget':'999999'}}
    with pytest.raises(ValueError): select_offer(owner,SelectionInput(selection_id=s['id'],offer_id=oid,quantity=qty))
    with Session() as db: assert db.scalar(select(func.count(Proposal.id)))==0

async def test_forged_graph_resume_does_not_select():
    from mcp_server.client import connect
    async def parser(_): return Requirements(category='laptop',budget=5000),0,0
    async with connect() as session:
        g=build_graph(InMemorySaver(),session,parser)
        config={'configurable':{'thread_id':uuid.uuid4().hex}}
        s=await g.ainvoke(dict(message='test',email='student@example.com',session_id='owner',steps=0,trajectory=[]),config)
        assert 'selection' in s and 'proposal' not in s
        result=await g.ainvoke(Command(resume={'offer_id':1,'approved':True}),config)
        assert result['status']=='error' and result['stop_reason']=='trusted_product_selection_required'
        assert 'proposal' not in result and 'order' not in result


def test_api_alternative_quantity_and_repeated_selection():
    seed_variants()
    with patch('smtplib.SMTP'),TestClient(app) as c:
        headers={'Authorization':'Bearer '+c.post('/sessions').json()['token']}
        other={'Authorization':'Bearer '+c.post('/sessions').json()['token']}
        state=c.post('/structured-request',headers=headers,json={'email':'student@example.com','requirements':{'category':'laptop','budget':'5000','intended_use':['programming']}}).json()
        assert state['status']=='awaiting_selection'
        path='/runs/'+state['thread_id']; body={'selection_id':state['selection']['id'],'offer_id':state['comparison'][1]['id'],'quantity':2}
        assert c.post(path+'/approval',headers=headers,json={'proposal_id':body['selection_id'],'proposal_hash':'forged','approve':True}).status_code==409
        assert c.post(path+'/selection',headers=other,json=body).status_code==404
        assert c.post(path+'/selection',headers=headers,json={**body,'budget':'1000000'}).status_code==422
        assert c.post(path+'/selection',headers=headers,json={**body,'approved':True}).status_code==422
        assert c.post(path+'/selection',headers=headers,json={**body,'offer_id':999}).status_code==409
        chosen=c.post(path+'/selection',headers=headers,json=body)
        assert chosen.status_code==200,chosen.text
        s=chosen.json(); assert s['status']=='awaiting_approval' and 'order' not in s
        assert s['proposal']['offer_id']==body['offer_id'] and s['proposal']['quantity']==2
        again=c.post(path+'/selection',headers=headers,json=body).json()
        assert again['status']=='awaiting_approval' and again['steps']==s['steps']
        assert c.get(path,headers=headers).json()['status']=='awaiting_approval'
        p=s['proposal']
        done=c.post(path+'/approval',headers=headers,json={'proposal_id':p['id'],'proposal_hash':p['hash'],'approve':True}).json()
        assert done['status']=='success' and done['steps']==10
        assert len(c.get('/orders',headers=headers).json())==1


def test_both_checkpoints_survive_backend_restart():
    with TestClient(app) as c:
        headers={'Authorization':'Bearer '+c.post('/sessions').json()['token']}
        s=c.post('/structured-request',headers=headers,json={'email':'student@example.com','requirements':{'category':'laptop','budget':'5000'}}).json()
        path='/runs/'+s['thread_id']
        choice={'selection_id':s['selection']['id'],'offer_id':s['comparison'][0]['id'],'quantity':1}
    with TestClient(app) as c:
        assert c.get(path,headers=headers).json()['status']=='awaiting_selection'
        s=c.post(path+'/selection',headers=headers,json=choice).json()
        assert s['status']=='awaiting_approval'
        p=s['proposal']
    with patch('smtplib.SMTP'),TestClient(app) as c:
        assert c.get(path,headers=headers).json()['status']=='awaiting_approval'
        s=c.post(path+'/approval',headers=headers,json={'proposal_id':p['id'],'proposal_hash':p['hash'],'approve':True}).json()
        assert s['status']=='success' and s['steps']==10
        assert len(c.get('/orders',headers=headers).json())==1
