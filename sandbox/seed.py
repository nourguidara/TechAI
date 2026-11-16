from decimal import Decimal
from sqlalchemy import select
from backend.database import init_db,Session
from backend.models import Product,Offer

def seed():
    init_db()
    with Session.begin() as db:
        for i,category in enumerate(('laptop','desktop','tablet'),1):
            signature='DEMO-'+category
            if db.scalar(select(Product).where(Product.signature==signature)): continue
            p=Product(signature=signature,category=category,brand='Lenovo',model='Demo '+category,
                name='DEMO Lenovo '+category,processor='Intel Core i5',ram_gb=16,storage_gb=512,storage_type='SSD',
                raw_specifications={'origin':'synthetic evaluation fixture; not a real retailer offer'})
            db.add(p); db.flush()
            db.add(Offer(product_id=p.id,supplier_name='DEMO supplier',supplier_product_id=signature,
                price_tnd=Decimal('1500.000'),stock_status='in_stock',available_quantity=10,
                product_url='https://www.mytek.tn/demo-'+category+'.html',is_demo=True))
if __name__=='__main__':
    seed(); print('Seeded explicitly labeled DEMO offers (not real scraped data).')
