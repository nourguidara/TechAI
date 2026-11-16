import json
from collections import Counter
from sqlalchemy import select
from backend.database import Session
from backend.models import Offer
from backend.services.catalog import safe_url
from pathlib import Path
with Session() as db:
    offers=db.scalars(select(Offer)).all(); real=[o for o in offers if not o.is_demo]
    assert all(o.price_tnd>0 and safe_url(o.product_url) and o.scraped_at and o.stock_status in ('in_stock','out_of_stock','unknown') for o in real)
    assert len({o.product_url for o in real})==len(real)
    assert all(o.available_quantity is None or o.available_quantity>=0 for o in real)
    result={'real_offers':len(real),'demo_offers':len(offers)-len(real),
        'by_supplier':dict(Counter(o.supplier_name for o in real)),
        'by_category':dict(Counter(o.product.category for o in real)),
        'stock_status':dict(Counter(o.stock_status for o in real)),
        'specification_coverage':{k:sum(getattr(o.product,k) is not None for o in real) for k in ['brand','processor','ram_gb','storage_gb','storage_type','screen_size','operating_system']},
        'validation':'passed: positive prices, allowed source URLs, timestamps, stock enum, quantity validity, unique source URLs'}
Path('eval/catalog-verification.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
