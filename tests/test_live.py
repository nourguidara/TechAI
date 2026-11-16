import os
import pytest
from agent.graph import parse_openai
@pytest.mark.live
@pytest.mark.skipif(os.getenv('RUN_LIVE_OPENAI')!='1',reason='Opt in with RUN_LIVE_OPENAI=1')
async def test_openai_extraction():
    r,tokens,cost=await parse_openai('Je veux 3 PC portables Lenovo, 16 Go RAM, SSD 512 Go, budget total 6000 TND.')
    assert r.category=='laptop' and r.quantity==3 and r.budget==6000 and r.min_ram==16
    assert tokens>0
