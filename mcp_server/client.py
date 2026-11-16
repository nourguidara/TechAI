import asyncio, json, os, sys
from contextlib import asynccontextmanager
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@asynccontextmanager
async def connect():
    params=StdioServerParameters(command=sys.executable,args=['-m','mcp_server.server'],env=dict(os.environ))
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as session:
            await asyncio.wait_for(session.initialize(),30)
            yield session

async def invoke(session,name,args):
    result=await asyncio.wait_for(session.call_tool(name,{'data':args}),30)
    if result.is_error: raise ValueError('mcp_tool_error: '+str(result.content)[:500])
    if result.structured_content is not None:
        value=result.structured_content
        return value.get('result',value) if isinstance(value,dict) else value
    texts=[c.text for c in result.content if c.type=='text']
    return json.loads(texts[0]) if len(texts)==1 else [json.loads(t) for t in texts]
