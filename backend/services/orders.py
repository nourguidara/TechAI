import hashlib, json, uuid
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select, text
from backend.database import Session
from backend.models import Proposal, Order, OrderItem, Notification, Offer, now
from backend.schemas import Requirements
from backend.services.catalog import matches

def digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def make_proposal(session_id, email, requirements, offer_id):
    r=Requirements.model_validate(requirements)
    with Session.begin() as db:
        o=db.get(Offer,offer_id)
        if o is None or not matches(o,r): raise ValueError('offer_no_longer_eligible')
        payload=dict(offer_id=o.id, product_name=o.product.name, supplier=o.supplier_name,
            unit_price=str(o.price_tnd), quantity=r.quantity, total=str(o.price_tnd*r.quantity),
            budget=str(r.budget), email=email, requirements=r.model_dump(mode='json'))
        p=Proposal(id=uuid.uuid4().hex,user_session_id=session_id,proposal_payload=payload,
            proposal_hash=digest(payload),budget_limit_tnd=r.budget,total_amount_tnd=o.price_tnd*r.quantity,
            expires_at=now()+timedelta(minutes=30))
        db.add(p)
    return dict(id=p.id,hash=p.proposal_hash,**payload)

def approve(proposal_id, session_id, proposal_hash, decision):
    with Session() as db:
        db.execute(text('BEGIN IMMEDIATE'))
        p=db.get(Proposal,proposal_id)
        if p is None or p.user_session_id != session_id: raise ValueError('proposal_not_found')
        if p.proposal_hash != proposal_hash or digest(p.proposal_payload)!=proposal_hash: raise ValueError('proposal_changed')
        if p.status in ('approved','ordered') and decision: return
        if p.status != 'pending' or p.expires_at < now(): raise ValueError('proposal_not_pending_or_expired')
        p.status='approved' if decision else 'rejected'
        p.approved_at=now() if decision else None
        db.commit()

def order_dict(o):
    return dict(id=o.id, reference=o.order_reference, status=o.status,total=str(o.total_amount_tnd),
        created_at=o.created_at.isoformat(),email_status=o.notifications[0].status,
        items=[dict(name=i.product_name_snapshot,supplier=i.supplier_snapshot,quantity=i.quantity,
                    unit_price=str(i.unit_price_tnd),subtotal=str(i.subtotal_tnd)) for i in o.items])

def create_purchase_order(data):
    with Session() as db:
        db.execute(text('BEGIN IMMEDIATE'))
        previous=db.scalar(select(Order).where(Order.idempotency_key==data.idempotency_key))
        if previous:
            if previous.proposal_id != data.proposal_id: raise ValueError('idempotency_conflict')
            return order_dict(previous)
        previous=db.scalar(select(Order).where(Order.proposal_id==data.proposal_id))
        if previous: return order_dict(previous)
        p=db.get(Proposal,data.proposal_id)
        if not p or p.status != 'approved' or not p.approved_at: raise ValueError('trusted_approval_required')
        if p.expires_at < now(): raise ValueError('proposal_expired')
        v=p.proposal_payload
        if digest(v)!=p.proposal_hash: raise ValueError('proposal_changed')
        r=Requirements.model_validate(v['requirements'])
        offer=db.get(Offer,v['offer_id'])
        if not offer or not matches(offer,r): raise ValueError('offer_no_longer_eligible')
        total=offer.price_tnd*r.quantity
        if offer.price_tnd != Decimal(v['unit_price']) or total != Decimal(v['total']): raise ValueError('price_changed_reapproval_required')
        if r.quantity!=v['quantity'] or r.budget!=p.budget_limit_tnd or total!=p.total_amount_tnd or total>p.budget_limit_tnd: raise ValueError('budget_or_quantity_integrity')
        o=Order(proposal_id=p.id,user_session_id=p.user_session_id,order_reference='TS-'+uuid.uuid4().hex[:12].upper(),
            user_email=v['email'],approved_at=p.approved_at,budget_limit_tnd=p.budget_limit_tnd,
            total_amount_tnd=total,idempotency_key=data.idempotency_key)
        db.add(o); db.flush()
        db.add(OrderItem(order_id=o.id,offer_id=offer.id,product_name_snapshot=v['product_name'],
            supplier_snapshot=v['supplier'],unit_price_tnd=offer.price_tnd,quantity=r.quantity,subtotal_tnd=total))
        db.add(Notification(order_id=o.id,recipient=v['email'],idempotency_key='email-'+p.id))
        p.status='ordered'
        db.commit(); db.refresh(o)
        return order_dict(o)
