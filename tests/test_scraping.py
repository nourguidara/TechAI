from decimal import Decimal
import pytest
from scraping.normalize import money,capacity,specs,stock
@pytest.mark.parametrize('text,expected',[('2.499,000 DT','2499.000'),('2499.000 TND','2499.000'),('2 499,000 DT','2499.000')])
def test_price(text,expected): assert money(text)==Decimal(expected)
@pytest.mark.parametrize('text,expected',[('16 Go',16),('16GB DDR4',16),('512 Go SSD',512),('1 To SSD',1024)])
def test_capacity(text,expected): assert capacity(text)==expected
def test_specs():
    s=specs('Lenovo RAM 16 Go, 512 Go SSD, Intel Core i5-1235U')
    assert s['ram_gb']==16 and s['storage_gb']==512 and s['storage_type']=='SSD'
def test_unknown_stock(): assert stock('')=='unknown'
def test_missing_specs(): assert specs('Ordinateur')['ram_gb'] is None


def test_saved_real_metadata():
    from pathlib import Path
    from scrapling import Selector
    from scraping.parser import parse_product
    page=Selector(Path('tests/fixtures/spacenet_product.html').read_text(encoding='utf-8'))
    record=parse_product(page,'https://spacenet.tn/pc-portable-tunisie/103971-pc.html','laptop','spacenet')
    assert record.price==Decimal('1099.000')
    assert record.specifications['ram_gb']==8
    assert record.specifications['storage_gb']==128
    assert record.stock_status=='in_stock'
    assert record.available_quantity is None

def test_refresh_dedup():
    from pathlib import Path
    from scrapling import Selector
    from scraping.parser import parse_product
    from scraping.refresh_catalog import save
    page=Selector(Path('tests/fixtures/spacenet_product.html').read_text(encoding='utf-8'))
    record=parse_product(page,'https://spacenet.tn/pc-portable-tunisie/103971-pc.html','laptop','spacenet')
    assert save(record)=='inserted'
    assert save(record)=='updated'
