"""Seven tool-output attacks are specified in scenarios.json and executed by trajectory_eval."""
import json
from pathlib import Path
def scenarios():
    return [c for c in json.loads(Path('eval/scenarios.json').read_text()) if c['category']=='injection']
