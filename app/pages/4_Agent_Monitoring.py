import streamlit as st
from app.ui import setup,api
setup('Agent Monitoring')
rows=api('GET','/runs')
a,b,c,d=st.columns(4)
a.metric('Runs',len(rows)); b.metric('Successful',sum(r['status']=='success' for r in rows))
c.metric('Failed',sum(r['status']=='error' for r in rows)); d.metric('Rejected',sum(r['status']=='rejected' for r in rows))
if rows:
    st.metric('Average steps',round(sum(r['steps'] for r in rows)/len(rows),2))
    st.dataframe([{k:v for k,v in r.items() if k!='trajectory'} for r in rows],hide_index=True)
    for r in rows:
        with st.expander(r['id']):
            st.json(r['trajectory'])
            if st.button('Find LangSmith trace',key=r['id']):
                trace=api('GET','/runs/'+r['id']+'/trace')
                if trace.get('url'): st.link_button('Open trace',trace['url'])
                else: st.info(trace['status'])
st.caption('Cost is unknown unless token pricing is configured. Offline evaluation uses no model tokens.')
