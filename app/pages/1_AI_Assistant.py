import streamlit as st
from app.ui import setup,api,product
setup('AI Procurement Assistant')
st.caption('Describe your request in English or French. Include category, quantity and total budget.')
email=st.text_input('Confirmation email',value='student@example.com')
with st.expander('Structured request - no OpenAI credits required'):
    st.caption('Explicit manual input. This mode does not interpret natural language with AI.')
    with st.form('structured'):
        cat=st.selectbox('Equipment category',['laptop','desktop','tablet'])
        qty=st.number_input('Quantity',1,100,1)
        budget=st.number_input('Total budget (TND)',min_value=1.0,value=5000.0,step=100.0)
        ram=st.number_input('Minimum RAM (GB)',0,1024,0)
        storage=st.number_input('Minimum storage (GB)',0,100000,0)
        brands=st.text_input('Brands, comma separated (optional)')
        if st.form_submit_button('Find and compare offers'):
            with st.spinner('Searching the catalog?'):
                st.session_state.result=api('POST','/structured-request',json={'email':email,'requirements':{
                    'category':cat,'quantity':qty,'budget':str(budget),'min_ram':ram,'min_storage':storage,
                    'brands':[b.strip() for b in brands.split(',') if b.strip()]}})
            st.rerun()

if 'messages' not in st.session_state: st.session_state.messages=[]
for role,text in st.session_state.messages:
    with st.chat_message(role): st.write(text)
message=st.chat_input('3 Lenovo laptops, 16 GB RAM, 512 GB SSD, total budget 6000 TND')
if message:
    st.session_state.messages.append(('user',message))
    with st.spinner('Checking requirements, offers and budget...'):
        r=api('POST','/chat',json={'message':'\n'.join(text for role,text in st.session_state.messages[-8:] if role=='user'),'email':email})
    st.session_state.result=r
    text=r.get('explanation') or r.get('stop_reason') or r['status']
    st.session_state.messages.append(('assistant',text)); st.rerun()
r=st.session_state.get('result')
@st.dialog('Purchase Order Confirmed')
def confirmed(order,email_status):
    st.success(order['reference']); st.write('Total: '+order['total']+' TND'); st.write(order['status'])
    if email_status=='sent': st.success('Confirmation email sent to the configured SMTP server.')
    else: st.warning('Order saved. Email status: '+email_status)
if r:
    st.caption('Agent status: '+r['status']+' | Steps: '+str(r.get('steps',0)))
    if r.get('comparison'):
        st.subheader('Compared offers')
        st.dataframe(r['comparison'],hide_index=True)
        product(r['comparison'][0])
    if r.get('proposal'):
        p=r['proposal']; st.subheader('Purchase proposal')
        st.write(p['product_name']+' | '+p['supplier'])
        st.write(f"{p['quantity']} | {p['unit_price']} TND = {p['total']} TND")
        st.write('Budget: '+p['budget']+' TND | Email: '+p['email'])
        st.caption('Merchandise total only; shipping is not quoted. Published stock may not specify exact quantity. Internal sandbox order only.')
        if r['status']=='awaiting_approval':
            a,b=st.columns(2)
            yes=a.button('Confirm purchase order',type='primary'); no=b.button('Reject')
            if yes or no:
                with st.spinner('Saving your decision...'):
                    result=api('POST','/runs/'+r['thread_id']+'/approval',json={'proposal_id':p['id'],'proposal_hash':p['hash'],'approve':yes})
                st.session_state.result=result
                if result.get('order'): confirmed(result['order'],result.get('email_result',{}).get('status','pending'))
                else: st.info(result.get('stop_reason',result['status']))
