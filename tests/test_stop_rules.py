from agent.stop_rules import consume
from backend.config import settings
import pytest

def test_bound():
    state={}
    for _ in range(settings.max_agent_steps): consume(state,'attempt')
    with pytest.raises(RuntimeError,match='step_limit'): consume(state,'attempt')
    assert state['steps']==settings.max_agent_steps
