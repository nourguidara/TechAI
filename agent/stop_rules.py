from backend.config import settings

def consume(state, name, args=None):
    if state.get('steps',0) >= settings.max_agent_steps:
        raise RuntimeError('step_limit')
    state['steps']=state.get('steps',0)+1
    state['trajectory']=[*state.get('trajectory',[]),dict(step=state['steps'],name=name,args=args or {})]
