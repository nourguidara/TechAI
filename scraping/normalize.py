import re, unicodedata
from decimal import Decimal, InvalidOperation

def plain(text):
    return ''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c)).lower()

def money(value):
    text=re.sub(r'[^0-9,.]','',str(value))
    if ',' in text and '.' in text:
        if text.rfind(',')>text.rfind('.'): text=text.replace('.','').replace(',','.')
        else: text=text.replace(',','')
    elif ',' in text: text=text.replace(',','.')
    try: result=Decimal(text)
    except InvalidOperation: raise ValueError('malformed_price')
    if not result.is_finite() or result<=0 or result>10000000: raise ValueError('invalid_price')
    return result.quantize(Decimal('.001'))

def capacity(text):
    m=re.search(r'(\d+(?:[.,]\d+)?)\s*(go|gb|to|tb)\b',plain(text))
    if not m: return None
    return int(Decimal(m[1].replace(',','.'))*(1024 if m[2] in ('to','tb') else 1))

def specs(text,attributes=None):
    t=plain(text); attrs={plain(k):v for k,v in (attributes or {}).items()}
    ram=None; storage=None; storage_type=None; processor=None; screen=None; os_name=None
    for key,value in attrs.items():
        if key == 'memoire' or any(k in key for k in ('memoire ram','ram','memoire vive')): ram=capacity(value)
        if any(k in key for k in ('disque dur','stockage','storage')):
            storage=capacity(value)
            storage_type=next((x for x in ('SSD','HDD','eMMC') if x.lower() in value.lower()),None)
        if any(k in key for k in ('processeur','processor')): processor=value.strip()
        if 'systeme' in key or 'operating' in key: os_name=value.strip()
        if ('taille' in key and 'ecran' in key) or 'screen size' in key:
            m=re.search(r'\d+(?:[.,]\d+)?',value)
            if m: screen=float(m[0].replace(',','.'))
    if ram is None:
        m=re.search(r'(?:ram|memoire(?: vive)?)\s*[:\-]?\s*(\d+\s*(?:go|gb))',t) or re.search(r'(\d+\s*(?:go|gb))\s*(?:ram|ddr[345])',t)
        if m: ram=capacity(m[1])
    if storage is None:
        m=re.search(r'(\d+(?:[.,]\d+)?\s*(?:go|gb|to|tb))\s*(ssd|hdd|emmc)',t) or re.search(r'(?:ssd|hdd|stockage|disque dur)\s*[:\-]?\s*(\d+(?:[.,]\d+)?\s*(?:go|gb|to|tb))',t)
        if m:
            storage=capacity(m[1]); storage_type=next((x for x in ('SSD','HDD','eMMC') if x.lower() in m[0]),None)
    if processor is None:
        m=re.search(r'(?:intel\s+)?(?:core\s+)?i[3579](?:[\s-]+\d{4,5}[a-z]*)?|(?:amd\s+)?ryzen\s+[3579](?:\s+\d{4}[a-z]*)?',t)
        if m: processor=m[0]
    brand=next((b for b in ('Lenovo','Dell','HP','Asus','Acer','Apple','MSI','Samsung','Huawei','Honor','Chuwi','Blackview','Bmax') if re.search(r'\b'+b.lower()+r'\b',t)),None)
    return dict(brand=brand,processor=processor,ram_gb=ram,storage_gb=storage,storage_type=storage_type,screen_size=screen,operating_system=os_name)

def stock(text):
    value=plain(text)
    if any(s in value for s in ('outofstock','out of stock','rupture','epuise','hors stock')): return 'out_of_stock'
    if any(s in value for s in ('instock','in stock','en stock','disponible')) and 'indisponible' not in value: return 'in_stock'
    return 'unknown'
