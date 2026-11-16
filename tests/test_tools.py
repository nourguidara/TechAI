from datetime import timedelta
import pytest
from pydantic import ValidationError
from backend.database import Session
from backend.models import Offer,now
from backend.schemas import SearchInput,Requirements,BudgetInput
from backend.services.catalog import search_products,check_budget,safe_url

def request(**kw):
    return SearchInput(requirements=Requirements(**(dict(category='laptop',quantity=2,budget=4000)|kw)))
def test_search(): assert len(search_products(request()))==1
def test_budget(): assert check_budget(BudgetInput(offer_id=1,quantity=3,budget=4000))['valid'] is False
@pytest.mark.parametrize('field,value',[('stock_status','unknown'),('stock_status','out_of_stock'),('available_quantity',1),('scraped_at',now()-timedelta(days=10))])
def test_ineligible(field,value):
    with Session.begin() as db: setattr(db.get(Offer,1),field,value)
    assert search_products(request())==[]
@pytest.mark.parametrize('url',['javascript:alert(1)','https://evil.test/x','https://www.mytek.tn@evil.test/x','http://127.0.0.1/x'])
def test_url(url): assert safe_url(url) is None
def test_strict():
    with pytest.raises(ValidationError): Requirements(quantity=0)
    with pytest.raises(ValidationError): SearchInput(requirements={},approved=True)
