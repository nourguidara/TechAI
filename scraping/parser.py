import json,hashlib
from urllib.parse import urlsplit,urlunsplit
from pydantic import BaseModel,Field,ConfigDict
from decimal import Decimal
from typing import Literal
from scraping.normalize import specs,money,stock
from backend.services.catalog import safe_url

class ScrapedOffer(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name:str=Field(min_length=1,max_length=1000)
    category:Literal['laptop','desktop','tablet']
    supplier:str
    source_id:str
    url:str
    image:str|None=None
    price:Decimal=Field(gt=0,le=10000000,decimal_places=3)
    stock_status:Literal['in_stock','out_of_stock','unknown']
    available_quantity:int|None=Field(default=None,ge=0)
    specifications:dict
    raw:dict
    model:str|None=None
    signature:str

def objects(value):
    if isinstance(value,list):
        for v in value: yield from objects(v)
    elif isinstance(value,dict):
        yield value
        if '@graph' in value: yield from objects(value['@graph'])

def parse_product(page,url,category,supplier):
    product=None
    for script in page.css('script[type="application/ld+json"]::text').getall():
        try:
            for obj in objects(json.loads(script)):
                if obj.get('@type')=='Product': product=obj; break
        except (ValueError,TypeError): continue
    if not product: raise ValueError('structured_product_metadata_missing')
    offer=product.get('offers',{})
    if isinstance(offer,list):
        if len(offer)!=1: raise ValueError('ambiguous_offers')
        offer=offer[0]
    if offer.get('priceCurrency')!='TND': raise ValueError('unexpected_currency')
    raw={}
    names=page.css('.data-sheet dt'); values=page.css('.data-sheet dd')
    for key,value in zip(names,values): raw[key.get_all_text().strip()]=value.get_all_text().strip()
    for row in page.css('#product-attribute-specs-table tr'):
        keys=row.css('th'); vals=row.css('td')
        if keys and vals: raw[keys[0].get_all_text().strip()]=vals[0].get_all_text().strip()
    name=product.get('name','').strip(); description=product.get('description','')
    normalized=specs(name+' '+description,raw)
    brand=product.get('brand')
    if isinstance(brand,dict): brand=brand.get('name')
    if isinstance(brand,str): normalized['brand']=brand
    model=product.get('mpn') or product.get('model')
    source_id=str(product.get('productID') or product.get('sku') or url)
    p=urlsplit(url); canonical=urlunsplit((p.scheme,p.netloc,p.path,'',''))
    if not safe_url(canonical): raise ValueError('unsafe_source_url')
    image=product.get('image')
    if isinstance(image,list): image=image[0] if image else None
    if isinstance(image,dict): image=image.get('url')
    # Merge across retailers only with manufacturer identity AND complete configuration.
    identity=[normalized.get(k) for k in ('brand','processor','ram_gb','storage_gb','storage_type','screen_size','operating_system')]
    signature_data=[category,model,*identity] if model and all(x is not None for x in identity) else [canonical,*identity]
    signature=hashlib.sha256(json.dumps(signature_data,sort_keys=True).encode()).hexdigest()
    return ScrapedOffer(name=name,category=category,supplier=supplier,source_id=source_id,url=canonical,
        image=safe_url(image),price=money(offer['price']),stock_status=stock(offer.get('availability','')),
        specifications=normalized,raw={'attributes':raw,'description':description,'metadata':product},model=model,signature=signature)
