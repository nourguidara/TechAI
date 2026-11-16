import concurrent.futures
from decimal import Decimal
import pytest
from sqlalchemy import select,func
from backend.database import Session
from backend.models import Offer,Order,Proposal
from backend.schemas import Requirements,OrderInput
from backend.services.orders import make_proposal,approve,create_purchase_order

def proposal():
    return make_proposal('owner','student@example.com',Requirements(category='laptop',quantity=2,budget='4000',min_ram=16).model_dump(mode='json'),1)
def approved():
    p=proposal(); approve(p['id'],'owner',p['hash'],True); return p

def test_approval_required():
    p=proposal()
    with pytest.raises(ValueError,match='approval'): create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
def test_session_and_hash():
    p=proposal()
    with pytest.raises(ValueError): approve(p['id'],'attacker',p['hash'],True)
    with pytest.raises(ValueError): approve(p['id'],'owner','forged',True)
def test_rejection():
    p=proposal(); approve(p['id'],'owner',p['hash'],False)
    with pytest.raises(ValueError): create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
def test_concurrent_idempotency():
    p=approved(); args=OrderInput(proposal_id=p['id'],idempotency_key=p['id'])
    with concurrent.futures.ThreadPoolExecutor(4) as pool: results=list(pool.map(lambda _:create_purchase_order(args),range(8)))
    assert len({r['id'] for r in results})==1
    with Session() as db: assert db.scalar(select(func.count(Order.id)))==1

def test_price_change():
    p=approved()
    with Session.begin() as db: db.get(Offer,1).price_tnd=Decimal('1501')
    with pytest.raises(ValueError,match='price_changed'): create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
def test_tamper():
    p=approved()
    with Session.begin() as db:
        record=db.get(Proposal,p['id']); record.proposal_payload={**record.proposal_payload,'quantity':99}
    with pytest.raises(ValueError,match='changed'): create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
def test_snapshot():
    p=approved(); args=OrderInput(proposal_id=p['id'],idempotency_key=p['id']); create_purchase_order(args)
    with Session.begin() as db: db.get(Offer,1).price_tnd=Decimal('999')
    assert create_purchase_order(args)['total']=='3000.000'


def test_expired():
    from datetime import timedelta
    from backend.models import now
    p=approved()
    with Session.begin() as db: db.get(Proposal,p['id']).expires_at=now()-timedelta(seconds=1)
    with pytest.raises(ValueError,match='expired'): create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))

def test_transaction_rollback():
    from sqlalchemy import event
    from backend.models import OrderItem,Notification
    p=approved()
    def fail(*args): raise RuntimeError('simulated_database_failure')
    event.listen(OrderItem,'before_insert',fail)
    try:
        with pytest.raises(RuntimeError): create_purchase_order(OrderInput(proposal_id=p['id'],idempotency_key=p['id']))
    finally: event.remove(OrderItem,'before_insert',fail)
    with Session() as db:
        assert db.scalar(select(func.count(Order.id)))==0
        assert db.scalar(select(func.count(Notification.id)))==0
