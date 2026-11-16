import uuid
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from agent.graph import build_graph
from backend.schemas import Requirements
from backend.services.orders import approve
from backend.services.selection import select_offer
from backend.schemas import SelectionInput
from mcp_server.client import connect

async def parser(_): return Requirements(category='laptop',quantity=2,budget=4000),0,None
async def test_real_mcp_graph():
    async with connect() as session:
        tools=await session.list_tools()
        assert len(tools.tools)==6
        g=build_graph(InMemorySaver(),session,parser)
        config={'configurable':{'thread_id':uuid.uuid4().hex}}
        s=await g.ainvoke(dict(message='2 laptops budget 4000 TND',email='student@example.com',session_id='owner',steps=0,trajectory=[]),config)
        assert s.get('__interrupt__') and 'order' not in s, s
        assert 'proposal' not in s
        select_offer('owner',SelectionInput(selection_id=s['selection']['id'],offer_id=s['comparison'][0]['id'],quantity=2))
        s=await g.ainvoke(Command(resume=True),config)
        assert s.get('__interrupt__') and 'order' not in s
        p=s['proposal']; approve(p['id'],'owner',p['hash'],True)
        result=await g.ainvoke(Command(resume=True),config)
        assert result['status']=='success',result
        assert result['steps']<=12
        assert result['order']['total']=='3000.000'


async def test_timeout_recovery():
    attempts=0
    async def caller(name,args):
        nonlocal attempts
        attempts+=1
        if attempts<3: raise TimeoutError('synthetic timeout')
        return []
    g=build_graph(InMemorySaver(),None,parser,caller)
    s=await g.ainvoke(dict(message='test',email='student@example.com',session_id='owner',steps=0,trajectory=[]),{'configurable':{'thread_id':uuid.uuid4().hex}})
    assert s['status']=='no_feasible_offer' and attempts==3 and s['steps']==4

async def test_unsupported_clarification():
    async def unsupported(_): return Requirements(category='laptop',quantity=2,budget=4000,other_preferences='Unverified CPU equivalence'),0,None
    g=build_graph(InMemorySaver(),None,unsupported)
    s=await g.ainvoke(dict(message='test',email='student@example.com',session_id='owner',steps=0,trajectory=[]),{'configurable':{'thread_id':uuid.uuid4().hex}})
    assert s['status']=='clarification' and s['steps']==1
