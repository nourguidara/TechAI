import os
import httpx
import streamlit as st
BASE=os.getenv('API_BASE_URL','http://localhost:8000')
def setup(title):
    st.set_page_config(page_title=title+' | TechStock AI',page_icon=':material/computer:',layout='wide')
    st.markdown('<style>.stApp {background: #f5f7fb} h1,h2,h3{color:#12304a} [data-testid="stMetric"]{background:white;padding:18px;border-radius:12px}</style>',unsafe_allow_html=True)
    st.sidebar.title('TechStock AI')
    st.sidebar.caption('Tunisia | IT procurement')
    st.sidebar.info('Sandbox orders only. No retailer payments or purchases.')
    if 'token' not in st.session_state:
        try: st.session_state.token=httpx.post(BASE+'/sessions',timeout=10).json()['token']
        except Exception: st.error('Backend unavailable. Start FastAPI on port 8000.'); st.stop()
    st.title(title)

def api(method,path,**kwargs):
    try:
        r=httpx.request(method,BASE+path,headers={'Authorization':'Bearer '+st.session_state.token},timeout=420,**kwargs)
        r.raise_for_status(); return r.json()
    except Exception as exc: st.error('Request failed: '+str(exc)); st.stop()

def product(o):
    with st.container(border=True):
        if o.get('image_url'): st.image(o['image_url'],width=140)
        st.subheader(o['name']); st.caption(o['supplier']+' | '+('DEMO fixture' if o['is_demo'] else 'Scraped offer'))
        st.write(f"{o['price_tnd']} TND | {o['ram_gb'] or '?'} GB RAM | {o['storage_gb'] or '?'} GB {o['storage_type'] or ''}")
        st.write(o.get('processor') or 'Processor unknown')
        st.caption(o['stock_status']+' | Collected '+o['scraped_at'])
        if o.get('product_url'): st.link_button('Retailer source',o['product_url'])
