from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlsplit
from sqlalchemy import select
from backend.database import Session
from backend.models import Offer, now
from backend.config import settings
from backend.schemas import Requirements

HOSTS = {'www.tunisianet.com.tn','www.mytek.tn','spacenet.tn'}
def safe_url(url: str | None, demo=False):
    if not url: return None
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError:
        return None
    if p.scheme != 'https' or p.hostname not in HOSTS or p.username or p.password or port not in (None,443):
        return None
    return url

def serialize(o):
    p = o.product
    return dict(id=o.id, name=p.name, category=p.category, brand=p.brand, model=p.model,
        processor=p.processor, ram_gb=p.ram_gb, storage_gb=p.storage_gb, storage_type=p.storage_type,
        screen_size=p.screen_size, operating_system=p.operating_system,
        supplier=o.supplier_name, price_tnd=str(o.price_tnd), stock_status=o.stock_status,
        available_quantity=o.available_quantity, product_url=safe_url(o.product_url),
        image_url=safe_url(o.image_url), scraped_at=o.scraped_at.isoformat(), is_demo=o.is_demo)

def matches(o, r: Requirements):
    p = o.product
    if not r.category or not r.quantity or not r.budget: raise ValueError('missing_request_parameters')
    if p.category != r.category or o.stock_status != 'in_stock': return False
    if o.scraped_at < now()-timedelta(hours=settings.offer_max_age_hours): return False
    if o.available_quantity is not None and o.available_quantity < r.quantity: return False
    if not safe_url(o.product_url): return False
    if r.brands and (p.brand or '').lower() not in [b.lower() for b in r.brands]: return False
    if r.min_ram and (p.ram_gb is None or p.ram_gb < r.min_ram): return False
    if r.min_storage and (p.storage_gb is None or p.storage_gb < r.min_storage): return False
    if r.storage_type and p.storage_type != r.storage_type: return False
    if r.processor and r.processor.lower() not in (p.processor or '').lower(): return False
    return o.price_tnd > 0 and o.price_tnd * r.quantity <= r.budget

def search_products(data):
    with Session() as db:
        return [serialize(o) for o in db.scalars(select(Offer)).all() if matches(o,data.requirements)
                and (data.max_unit_price is None or o.price_tnd <= data.max_unit_price)][:100]

def compare_offers(data):
    with Session() as db:
        offers = [o for o in db.scalars(select(Offer).where(Offer.id.in_(data.offer_ids))).all() if matches(o,data.requirements)]
        offers.sort(key=lambda o: (o.price_tnd, -o.scraped_at.timestamp(), o.id))
        return [dict(**serialize(o), total_tnd=str(o.price_tnd*data.requirements.quantity),
            ranking_reason='Meets hard requirements; lowest total first, freshest data breaks ties.',
            stock_note='Quantity not published; sandbox order only.' if o.available_quantity is None else 'Published quantity sufficient.') for o in offers]

def get_offer_details(data):
    with Session() as db:
        o=db.get(Offer,data.offer_id)
        if o is None: raise ValueError('offer_not_found')
        return serialize(o)

def check_budget(data):
    with Session() as db:
        o=db.get(Offer,data.offer_id)
        if o is None: raise ValueError('offer_not_found')
        total=o.price_tnd*data.quantity
        return dict(total=str(total), budget=str(data.budget), remaining=str(data.budget-total), valid=0 < total <= data.budget)
