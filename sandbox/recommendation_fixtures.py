"""Synthetic variants for controlled ranking tests only; never seed the real catalog implicitly."""
from decimal import Decimal
from backend.database import Session
from backend.models import Product, Offer

VARIANTS = [
    ('memory','Lenovo',32,512,'Intel Core i5','2200'),
    ('storage','Acer',16,1024,'AMD Ryzen 5','2200'),
    ('budget','Lenovo',8,256,'Intel Core i3','1000'),
    ('incomplete','Dell',None,512,None,'700'),
]

def seed_variants():
    result={}
    with Session.begin() as db:
        for label,brand,ram,storage,cpu,price in VARIANTS:
            p=Product(signature='DEMO-variant-'+label,category='laptop',brand=brand,model=label,
                name='DEMO '+label,processor=cpu,ram_gb=ram,storage_gb=storage,storage_type='SSD',
                operating_system='Windows 11',raw_specifications={'origin':'synthetic ranking fixture'})
            db.add(p);db.flush()
            o=Offer(product_id=p.id,supplier_name='DEMO supplier',supplier_product_id='DEMO-'+label,
                price_tnd=Decimal(price),stock_status='in_stock',available_quantity=10,
                product_url='https://www.mytek.tn/demo-'+label+'.html',is_demo=True)
            db.add(o);db.flush();result[label]=o.id
    return result
