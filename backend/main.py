import asyncio, hashlib, secrets, uuid
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException, Depends
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from sqlalchemy import select
from backend.database import init_db, Session
from backend.config import settings
from backend.models import AgentRun, Offer, Order, now
from backend.schemas import ChatInput, ApprovalInput, EmailInput, StructuredInput, SelectionInput
from backend.services.orders import approve, order_dict
from backend.services.catalog import serialize
from backend.services.selection import select_offer
from backend.services.email import send_confirmation_email
from agent.graph import build_graph
from mcp_server.client import connect

@asynccontextmanager
async def lifespan(app):
    init_db()
    async with connect() as mcp:
        async with AsyncSqliteSaver.from_conn_string(str(Path(settings.database_url.removeprefix('sqlite:///')).with_suffix('.checkpoints.db'))) as saver:
            app.state.graph=build_graph(saver,mcp)
            app.state.saver=saver; app.state.mcp=mcp
            app.state.lock=asyncio.Lock()
            yield
app=FastAPI(title='TechStock AI',lifespan=lifespan)

def session_id(authorization: str=Header(default='')):
    if not authorization.startswith('Bearer ') or len(authorization)<40: raise HTTPException(401,'Session required')
    return hashlib.sha256(authorization[7:].encode()).hexdigest()

@app.get('/health')
def health(): return {'status':'ok','mode':'sandbox'}
@app.post('/sessions')
def new_session(): return {'token':secrets.token_urlsafe(32)}

def run_status(result, pending=None):
    if pending:
        if 'human_selection' in pending: return 'awaiting_selection'
        if 'human_approval' in pending: return 'awaiting_approval'
    if result.get('__interrupt__'):
        kind=result['__interrupt__'][0].value.get('kind')
        return 'awaiting_selection' if kind=='product_selection' else 'awaiting_approval'
    return result.get('status','error')


def persist(thread,result,pending=None):
    with Session.begin() as db:
        r=db.get(AgentRun,thread)
        r.status=run_status(result,pending)
        r.steps_executed=result.get('steps',0); r.stop_reason=result.get('stop_reason')
        r.total_tokens=result.get('total_tokens',0); r.estimated_cost=result.get('estimated_cost')
        r.trajectory=result.get('trajectory',[])
        if r.status not in ('awaiting_approval','awaiting_selection'): r.completed_at=now()
    return {k:v for k,v in result.items() if k not in ('__interrupt__','session_id','email','message')} | {'thread_id':thread,'status':r.status}

@app.post('/chat')
async def chat(body:ChatInput,sid=Depends(session_id)):
    thread=uuid.uuid4().hex
    with Session.begin() as db: db.add(AgentRun(id=thread,thread_id=thread,user_session_id=sid))
    async with app.state.lock:
        result=await app.state.graph.ainvoke(dict(message=body.message,email=str(body.email),session_id=sid,steps=0,trajectory=[]),
            config={'configurable':{'thread_id':thread},'recursion_limit':30,'run_id':uuid.UUID(thread)})
    return persist(thread,result)

@app.post('/runs/{thread}/approval')
async def approval(thread:str,body:ApprovalInput,sid=Depends(session_id)):
    async with app.state.lock:
        with Session() as db:
            r=db.get(AgentRun,thread)
            if not r or r.user_session_id!=sid: raise HTTPException(404,'Run not found')
        config={'configurable':{'thread_id':thread},'recursion_limit':30,'run_id':uuid.UUID(thread)}
        state=await app.state.graph.aget_state(config)
        if state.next and 'human_approval' not in state.next: raise HTTPException(409,'Product selection is required before purchase approval')
        if state.values.get('proposal',{}).get('id')!=body.proposal_id: raise HTTPException(409,'Proposal mismatch')
        try: approve(body.proposal_id,sid,body.proposal_hash,body.approve)
        except ValueError as exc: raise HTTPException(409,str(exc))
        if not state.next: return persist(thread,state.values)
        result=await app.state.graph.ainvoke(Command(resume=True),config=config)
        return persist(thread,result)

@app.get('/catalog')
def catalog(sid=Depends(session_id)):
    with Session() as db: return [serialize(o) for o in db.scalars(select(Offer)).all()]
@app.get('/orders')
def orders(sid=Depends(session_id)):
    with Session() as db: return [order_dict(o) for o in db.scalars(select(Order).where(Order.user_session_id==sid)).all()]
@app.post('/orders/{order_id}/retry-email')
def retry_email(order_id:int,sid=Depends(session_id)):
    with Session() as db:
        o=db.get(Order,order_id)
        if not o or o.user_session_id!=sid: raise HTTPException(404,'Order not found')
    return send_confirmation_email(EmailInput(order_id=order_id))
@app.get('/runs')
def runs(sid=Depends(session_id)):
    with Session() as db:
        return [dict(id=r.id,status=r.status,steps=r.steps_executed,stop_reason=r.stop_reason,tokens=r.total_tokens,
            estimated_cost=r.estimated_cost,trajectory=r.trajectory,
            latency=(r.completed_at-r.started_at).total_seconds() if r.completed_at else None)
            for r in db.scalars(select(AgentRun).where(AgentRun.user_session_id==sid)).all()]

@app.post('/structured-request')
async def structured(body:StructuredInput,sid=Depends(session_id)):
    async def parser(_): return body.requirements,0,0.0
    thread=uuid.uuid4().hex
    with Session.begin() as db: db.add(AgentRun(id=thread,thread_id=thread,user_session_id=sid))
    async with app.state.lock:
        graph=build_graph(app.state.saver,app.state.mcp,parser)
        result=await graph.ainvoke(dict(message='User-entered structured request (no model)',email=str(body.email),session_id=sid,steps=0,trajectory=[]),
            config={'configurable':{'thread_id':thread},'recursion_limit':30,'run_id':uuid.UUID(thread)})
    return persist(thread,result)

@app.get('/runs/{thread}/trace')
async def trace_link(thread:str,sid=Depends(session_id)):
    with Session() as db:
        r=db.get(AgentRun,thread)
        if not r or r.user_session_id!=sid: raise HTTPException(404,'Run not found')
    if not settings.langsmith_tracing: return {'url':None,'status':'disabled'}
    try:
        from langsmith import Client
        client=Client(timeout_ms=5000)
        project=await asyncio.to_thread(client.read_project,project_name=settings.langsmith_project)
        result=await client.runs.get_url(thread,project_id=str(project.id),trace_id=thread)
        return {'url':result.url,'status':'available'}
    except Exception:
        return {'url':None,'status':'Trace not indexed or tracing unavailable'}


@app.post('/runs/{thread}/selection')
async def selection(thread:str,body:SelectionInput,sid=Depends(session_id)):
    async with app.state.lock:
        with Session() as db:
            r=db.get(AgentRun,thread)
            if not r or r.user_session_id!=sid: raise HTTPException(404,'Run not found')
        config={'configurable':{'thread_id':thread},'recursion_limit':30,'run_id':uuid.UUID(thread)}
        state=await app.state.graph.aget_state(config)
        if state.values.get('selection',{}).get('id')!=body.selection_id: raise HTTPException(409,'Selection mismatch')
        if 'human_selection' not in state.next and 'proposal' not in state.values:
            raise HTTPException(409,'Run is not awaiting product selection')
        try: select_offer(sid,body)
        except ValueError as exc: raise HTTPException(409,str(exc))
        if 'human_selection' not in state.next:
            return persist(thread,state.values,state.next)
        result=await app.state.graph.ainvoke(Command(resume=True),config=config)
        return persist(thread,result)


@app.get('/runs/{thread}')
async def run_details(thread:str,sid=Depends(session_id)):
    with Session() as db:
        r=db.get(AgentRun,thread)
        if not r or r.user_session_id!=sid: raise HTTPException(404,'Run not found')
    state=await app.state.graph.aget_state({'configurable':{'thread_id':thread}})
    return {k:v for k,v in state.values.items() if k not in ('session_id','email','message')} | {
        'thread_id':thread,'status':run_status(state.values,state.next)}
