from decimal import Decimal
import streamlit as st
from app.ui import setup,api,product
setup('AI Procurement Assistant')
st.caption('Describe your needs in English or French and include a total budget. Quantity defaults to one.')
email=st.text_input('Confirmation email',value='student@example.com')
with st.expander('Structured request - no OpenAI credits required'):
    st.caption('Manual input using the same recommendation, selection and approval safeguards.')
    with st.form('structured'):
        cat=st.selectbox('Equipment category',['laptop','desktop','tablet'])
        use=st.multiselect('Intended use',['general','programming','machine_learning','gaming','study','notes','media','video_editing','work'])
        priorities=st.multiselect('Priorities',['ram','storage','value','budget_headroom','data_confidence','portability','battery','graphics'])
        qty=st.number_input('Requested quantity',1,100,1)
        budget=st.number_input('Total budget (TND)',min_value=1.0,value=3000.0,step=100.0)
        ram=st.number_input('Hard minimum RAM (GB)',0,1024,0)
        storage=st.number_input('Hard minimum storage (GB)',0,100000,0)
        brands=st.text_input('Required brands, comma separated (optional)')
        preferred=st.text_input('Preferred brands, comma separated (optional)')
        soft=st.text_input('Other soft preferences (may remain unverified)')
        if st.form_submit_button('Find recommendations'):
            with st.spinner('Ranking eligible offers...'):
                st.session_state.result=api('POST','/structured-request',json={'email':email,'requirements':{
                    'category':cat,'quantity':qty,'budget':str(budget),'min_ram':ram,'min_storage':storage,
                    'brands':[b.strip() for b in brands.split(',') if b.strip()],
                    'preferred_brands':[b.strip() for b in preferred.split(',') if b.strip()],
                    'intended_use':use,'priorities':priorities,'soft_preferences':[soft] if soft else []}})
            st.rerun()

if 'messages' not in st.session_state: st.session_state.messages=[]
for role,text in st.session_state.messages:
    with st.chat_message(role): st.write(text)
message=st.chat_input('A laptop for Python programming, around 3000 TND')
if message:
    st.session_state.messages.append(('user',message))
    with st.spinner('Understanding your needs and comparing offers...'):
        r=api('POST','/chat',json={'message':'\n'.join(text for role,text in st.session_state.messages[-8:] if role=='user'),'email':email})
    st.session_state.result=r
    st.session_state.messages.append(('assistant',r.get('explanation') or r.get('stop_reason') or r['status']))
    st.rerun()

@st.dialog('Purchase Order Confirmed')
def confirmed(order,email_status):
    st.success(order['reference']); st.write('Total: '+order['total']+' TND'); st.write(order['status'])
    if email_status=='sent': st.success('Confirmation email accepted by the configured SMTP server.')
    else: st.warning('Order saved. Email status: '+email_status)

r=st.session_state.get('result')
if r:
    st.caption('Agent status: '+r['status']+' | Steps: '+str(r.get('steps',0))+' / 12')
    if r.get('stop_reason') and r['status'] not in ('success','awaiting_selection','awaiting_approval'):
        st.info(r.get('explanation') or r['stop_reason'])
    if r.get('selection'):
        if r['status']=='awaiting_selection':
            st.info('1. Select a product and quantity. 2. Review the exact proposal. 3. Confirm separately. No order is created by selection.')
            quantity=st.number_input('Quantity to purchase',1,100,int(r['requirements']['quantity']),key='quantity_'+r['thread_id'])
        else:
            quantity=r['requirements']['quantity']
        st.caption('Suitability is an estimate from listed specifications, not a benchmark or performance guarantee. Change budget or requirements by starting a new request.')
        for o in r['selection']['recommendations']:
            with st.container(border=True):
                st.subheader(o['label'])
                product(o)
                st.write(o['ranking_reason'])
                for fact in o['facts']: st.write(fact)
                for tradeoff in o['tradeoffs']: st.write('Tradeoff: '+tradeoff)
                for limitation in o['limitations']: st.caption(limitation)
                st.caption(o['stock_note'])
                total=Decimal(o['price_tnd'])*quantity
                remaining=Decimal(r['requirements']['budget'])-total
                st.write(f'Merchandise total: {total:.3f} TND | Remaining budget: {remaining:.3f} TND')
                over=remaining<0 or (o['available_quantity'] is not None and quantity>o['available_quantity'])
                if over: st.warning('This quantity exceeds the budget or published stock.')
                if r['status']=='awaiting_selection' and st.button('Select Product',key='select_'+str(o['id']),disabled=over):
                    with st.spinner('Revalidating your selection...'):
                        st.session_state.result=api('POST','/runs/'+r['thread_id']+'/selection',json={
                            'selection_id':r['selection']['id'],'offer_id':o['id'],'quantity':quantity})
                    st.rerun()
    if r.get('proposal'):
        p=r['proposal']; st.subheader('Final purchase proposal - separate approval required')
        st.write(p['product_name']+' | '+p['supplier'])
        st.write(f"{p['quantity']} x {p['unit_price']} TND = {p['total']} TND")
        st.write('Budget: '+p['budget']+' TND | Email: '+p['email'])
        st.caption('Merchandise total only; shipping is not quoted. Internal sandbox order, not a retailer purchase.')
        if r['status']=='awaiting_approval':
            a,b=st.columns(2)
            yes=a.button('Confirm purchase order',type='primary'); no=b.button('Reject')
            if yes or no:
                with st.spinner('Saving your decision...'):
                    result=api('POST','/runs/'+r['thread_id']+'/approval',json={'proposal_id':p['id'],'proposal_hash':p['hash'],'approve':yes})
                st.session_state.result=result
                if result.get('order'): confirmed(result['order'],result.get('email_result',{}).get('status','pending'))
                else: st.info(result.get('stop_reason',result['status']))
    if r.get('order'):
        st.success('Sandbox order: '+r['order']['reference'])
        st.write('Email: '+r['order']['email_status'])
