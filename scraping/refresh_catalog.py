import argparse,json,time,logging
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from scrapling.fetchers import Fetcher,FetcherSession
from scrapling.spiders import Spider
from protego import Protego
from sqlalchemy import select, or_, and_
from backend.config import settings
from backend.database import Session,init_db
from backend.models import Product,Offer,now
from scraping import mytek,tunisianet,spacenet
from scraping.parser import parse_product

USER_AGENT='TechStockAcademicBot/1.0'
FETCH=dict(timeout=25,impersonate=None,stealthy_headers=False,headers={'User-Agent':USER_AGENT},follow_redirects=False,retries=0)

def save(record):
    with Session.begin() as db:
        p=db.scalar(select(Product).where(Product.signature==record.signature))
        if p is None:
            p=Product(signature=record.signature,name=record.name,category=record.category,model=record.model,
                raw_specifications=record.raw,**record.specifications); db.add(p); db.flush()
        o=db.scalar(select(Offer).where(or_(Offer.product_url==record.url,and_(Offer.supplier_name==record.supplier,Offer.supplier_product_id==record.source_id))))
        inserted=o is None
        if o is None:
            o=Offer(product_id=p.id,supplier_name=record.supplier,supplier_product_id=record.source_id,product_url=record.url,
                price_tnd=record.price,stock_status=record.stock_status); db.add(o)
        o.product_url=record.url; o.product_id=p.id; o.price_tnd=record.price; o.stock_status=record.stock_status
        o.available_quantity=record.available_quantity; o.image_url=record.image; o.scraped_at=now()
        p.raw_specifications=record.raw; p.name=record.name
    return 'inserted' if inserted else 'updated'

class CatalogSpider(Spider):
    name='techstock-catalog'
    concurrent_requests=1
    concurrent_requests_per_domain=1
    max_blocked_retries=0
    robots_txt_obey=True
    logging_level=logging.INFO
    def __init__(self,source,category,rules,limit,delay):
        self.source=source; self.category=category; self.rules=rules; self.limit=limit
        self.download_delay=delay; self.start_urls=[source.CATEGORIES[category]]
        self.allowed_domains={urlsplit(source.ROOT).hostname}
        self.seen=set(); self.category_pages=0; self.halted=False
        self.report=dict(retailer=source.__name__.split('.')[-1],category=category,pages_visited=0,products_discovered=0,
            products_extracted=0,inserted=0,updated=0,errors=[],skipped_by_robots=0)
        super().__init__()
    def configure_sessions(self,manager): manager.add('default',FetcherSession(**FETCH))
    def allowed(self,url):
        return urlsplit(url).hostname in self.allowed_domains and self.rules.can_fetch(url,USER_AGENT)
    async def is_blocked(self,response):
        blocked=await super().is_blocked(response)
        if blocked:
            self.halted=True; self.report['errors'].append('blocked_http_'+str(response.status)); self.pause()
        return blocked
    async def on_error(self,request,error): self.report['errors'].append(type(error).__name__+': '+str(error)[:100])
    async def parse(self,response):
        self.report['pages_visited']+=1; self.category_pages+=1
        if self.halted or response.status!=200: return
        for link in response.css('a.product-thumbnail::attr(href), a.product-item-link::attr(href), h2.product-title a::attr(href)').getall():
            url=urljoin(response.url,link)
            if url in self.seen or len(self.seen)>=self.limit: continue
            if not self.allowed(url): self.report['skipped_by_robots']+=1; continue
            self.seen.add(url); self.report['products_discovered']+=1
            yield response.follow(url,callback=self.parse_product)
        if len(self.seen)<self.limit and self.category_pages<settings.scraping_max_pages:
            link=response.css('a.next::attr(href), a.action.next::attr(href), link[rel="next"]::attr(href)').get()
            if link:
                url=urljoin(response.url,link)
                if self.allowed(url): yield response.follow(url,callback=self.parse)
                else: self.report['skipped_by_robots']+=1
    async def parse_product(self,response):
        self.report['pages_visited']+=1
        if self.halted or response.status!=200: return
        try:
            record=parse_product(response,response.url,self.category,self.report['retailer'])
            kind=save(record); self.report[kind]+=1; self.report['products_extracted']+=1
            yield dict(url=record.url,price=str(record.price))
        except Exception as exc:
            self.report['errors'].append(str(exc)[:160]); self.logger.warning('Extraction failed: %s',exc)

def refresh(retailer='spacenet',category=None,limit=34):
    init_db(); reports=[]
    if retailer=='tunisianet':
        reports=[dict(retailer=retailer,category=category or 'all',products_extracted=0,errors=['Collection disabled: terms Article 9 prohibits catalog reproduction; obtain retailer permission.'])]
    else:
        source={'mytek':mytek,'spacenet':spacenet}[retailer]
        r=Fetcher.get(source.ROOT+'/robots.txt',**FETCH)
        if r.status!=200: raise RuntimeError('robots_unavailable_fail_closed')
        rules=Protego.parse(r.body.decode('utf-8',errors='replace'))
        delay=max(settings.scraping_request_delay,float(rules.crawl_delay(USER_AGENT) or 0),10 if retailer=='spacenet' else 2)
        for cat in ([category] if category else list(source.CATEGORIES)):
            if not rules.can_fetch(source.CATEGORIES[cat],USER_AGENT):
                reports.append(dict(retailer=retailer,category=cat,errors=['robots_disallow'])); continue
            time.sleep(delay)
            spider=CatalogSpider(source,cat,rules,limit,delay); start=time.perf_counter()
            result=spider.start()
            spider.report['robots_disallowed_count']=result.stats.robots_disallowed_count
            spider.report['failed_requests_count']=result.stats.failed_requests_count
            if result.stats.robots_disallowed_count and not spider.report['pages_visited']:
                spider.report['errors'].append('robots_check_failed_or_disallowed; no requests made')
            spider.report['execution_seconds']=time.perf_counter()-start
            reports.append(spider.report)
            print(json.dumps(spider.report),flush=True)
            if spider.halted: break
    Path('data').mkdir(exist_ok=True)
    Path('data/scrape-'+retailer+'.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    Path('data/scrape-'+retailer+'-'+now().strftime('%Y%m%dT%H%M%S')+'.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    return reports

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--retailer',choices=['spacenet','mytek','tunisianet'],default='spacenet')
    p.add_argument('--category',choices=['laptop','desktop','tablet']); p.add_argument('--limit',type=int,default=34)
    a=p.parse_args()
    if not 1<=a.limit<=200: p.error('limit must be between 1 and 200 per category')
    print(json.dumps(refresh(a.retailer,a.category,a.limit),indent=2))
