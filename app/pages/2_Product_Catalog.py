import streamlit as st
from app.ui import setup,api,product
setup('Product Catalog')
rows=api('GET','/catalog')
st.metric('Real collected offers',sum(not o['is_demo'] for o in rows))
query=st.text_input('Search products')
a,b,c=st.columns(3)
category=a.selectbox('Category',['All','laptop','desktop','tablet'])
brand=b.selectbox('Brand',['All']+sorted({o['brand'] for o in rows if o['brand']}))
supplier=c.selectbox('Supplier',['All']+sorted({o['supplier'] for o in rows}))
a,b,c=st.columns(3)
ram=a.number_input('Minimum RAM (GB)',0,1024,0)
storage=b.number_input('Minimum storage (GB)',0,100000,0)
price=c.number_input('Maximum price (TND)',0,1000000,1000000)
demo=st.checkbox('Show clearly labeled demo fixtures',False)
filtered=[o for o in rows if (demo or not o['is_demo']) and query.lower() in o['name'].lower()
    and (category=='All' or category==o['category']) and (brand=='All' or brand==o['brand'])
    and (supplier=='All' or supplier==o['supplier']) and (o['ram_gb'] or 0)>=ram
    and (o['storage_gb'] or 0)>=storage and float(o['price_tnd'])<=price]
st.caption(str(len(filtered))+' matching offers')
for o in filtered: product(o)
