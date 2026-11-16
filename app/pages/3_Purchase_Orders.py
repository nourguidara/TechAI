import streamlit as st
from app.ui import setup,api
setup('Purchase Orders')
rows=api('GET','/orders')
if not rows: st.info('Your confirmed sandbox orders will appear here.')
for o in rows:
    with st.expander(o['reference']+' | '+o['total']+' TND'):
        st.write(o['created_at']); st.write(o['status']); st.dataframe(o['items'],hide_index=True)
        st.write('Email: '+o['email_status'])
        if o['email_status'] in ('failed','pending') and st.button('Retry email',key=str(o['id'])):
            api('POST',f"/orders/{o['id']}/retry-email"); st.rerun()
