from unittest.mock import patch
from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_home_renders():
    with patch('httpx.post') as post:
        post.return_value.json.return_value={'token':'synthetic-session-token'}
        at=AppTest.from_file(Path('app/Home.py').resolve()).run(timeout=15)
        assert not at.exception
        assert at.title[0].value=='Procure with confidence'


def test_all_pages_render():
    with patch('httpx.post') as post, patch('httpx.request') as request:
        post.return_value.json.return_value={'token':'synthetic-session-token'}
        request.return_value.json.return_value=[]
        at=AppTest.from_file(Path('app/Home.py').resolve()).run(timeout=15)
        for page in ['1_AI_Assistant','2_Product_Catalog','3_Purchase_Orders','4_Agent_Monitoring']:
            at.switch_page('pages/'+page+'.py').run(timeout=15)
            assert not at.exception,page
