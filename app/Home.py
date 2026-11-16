import streamlit as st
from app.ui import setup
setup('Procure with confidence')
st.markdown('### Find the right equipment. Keep every purchase accountable.')
st.write('Compare Tunisian retailer offers, review your budget, and approve an exact purchase summary before a sandbox order is created.')
a,b,c=st.columns(3)
a.metric('Equipment categories','3'); b.metric('Approval','Required'); c.metric('Currency','TND')
st.page_link('pages/1_AI_Assistant.py',label='Open AI procurement assistant',icon=':material/chat:')
st.page_link('pages/2_Product_Catalog.py',label='Explore product catalog',icon=':material/search:')
st.info('Start the catalog scraper to collect real offers. Demo fixtures are labeled separately.')
