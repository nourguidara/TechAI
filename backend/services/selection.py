"""Trusted recommendation snapshots and human selection, separate from approval."""
import uuid
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import text
from backend.database import Session
from backend.models import ShoppingSelection, Offer, Proposal, now
from backend.schemas import Requirements, SearchInput, CompareInput, SelectionInput
from backend.services.catalog import search_products, compare_offers, matches
from backend.services.orders import digest


def prepare_selection(owner: str, requirements: dict) -> dict:
    r=Requirements.model_validate(requirements)
    # Recompute from trusted catalog instead of accepting a tool/client supplied selection list.
    candidates=search_products(SearchInput(requirements=r))
    ranked=compare_offers(CompareInput(requirements=r,offer_ids=[o['id'] for o in candidates])) if candidates else []
    if not ranked: raise ValueError('no_eligible_fresh_offer')
    payload=dict(requirements=r.model_dump(mode='json'),recommendations=ranked)
    with Session.begin() as db:
        record=ShoppingSelection(id=uuid.uuid4().hex,user_session_id=owner,payload=payload,
            payload_hash=digest(payload),expires_at=now()+timedelta(minutes=30))
        db.add(record)
    return dict(id=record.id,recommendations=ranked,expires_at=record.expires_at.isoformat())


def checked(record, owner):
    if not record or record.user_session_id!=owner: raise ValueError('selection_not_found')
    if digest(record.payload)!=record.payload_hash: raise ValueError('recommendations_changed')
    if record.expires_at<now(): raise ValueError('recommendations_expired_start_new_request')


def validate_choice(db, record, offer_id, quantity):
    choices={o['id']:o for o in record.payload['recommendations']}
    if offer_id not in choices: raise ValueError('offer_not_in_authorized_recommendations')
    r=Requirements.model_validate({**record.payload['requirements'],'quantity':quantity})
    offer=db.get(Offer,offer_id)
    if not offer or not matches(offer,r): raise ValueError('selection_unavailable_or_exceeds_budget')
    if offer.price_tnd!=Decimal(choices[offer_id]['price_tnd']): raise ValueError('recommendation_price_changed_start_new_request')
    return r,offer


def select_offer(owner: str, data: SelectionInput):
    with Session() as db:
        db.execute(text('BEGIN IMMEDIATE'))
        record=db.get(ShoppingSelection,data.selection_id); checked(record,owner)
        if record.status=='selected':
            if (record.selected_offer_id,record.selected_quantity)!=(data.offer_id,data.quantity):
                raise ValueError('selection_already_recorded_start_new_request')
            return  # Idempotent retry of the exact selection, never approval.
        if record.status!='pending': raise ValueError('selection_not_pending')
        validate_choice(db,record,data.offer_id,data.quantity)
        record.selected_offer_id=data.offer_id; record.selected_quantity=data.quantity
        record.status='selected'; record.selected_at=now(); db.commit()


def trusted_choice(selection_id,owner):
    with Session() as db:
        record=db.get(ShoppingSelection,selection_id); checked(record,owner)
        if record.status!='selected' or not record.selected_at: raise ValueError('trusted_product_selection_required')
        r,offer=validate_choice(db,record,record.selected_offer_id,record.selected_quantity)
        return dict(requirements=r.model_dump(mode='json'),offer_id=offer.id)


def selected_proposal(selection_id,owner,email):
    # One proposal per selection, even if the node is replayed after a checkpoint failure.
    with Session() as db:
        db.execute(text('BEGIN IMMEDIATE'))
        record=db.get(ShoppingSelection,selection_id); checked(record,owner)
        if record.status!='selected' or not record.selected_at: raise ValueError('trusted_product_selection_required')
        prior=db.get(Proposal,selection_id)
        if prior:
            if prior.user_session_id!=owner or digest(prior.proposal_payload)!=prior.proposal_hash: raise ValueError('proposal_changed')
            return dict(id=prior.id,hash=prior.proposal_hash,**prior.proposal_payload)
        r,offer=validate_choice(db,record,record.selected_offer_id,record.selected_quantity)
        payload=dict(offer_id=offer.id,product_name=offer.product.name,supplier=offer.supplier_name,
            unit_price=str(offer.price_tnd),quantity=r.quantity,total=str(offer.price_tnd*r.quantity),
            budget=str(r.budget),email=email,requirements=r.model_dump(mode='json'))
        p=Proposal(id=selection_id,user_session_id=owner,proposal_payload=payload,proposal_hash=digest(payload),
            budget_limit_tnd=r.budget,total_amount_tnd=offer.price_tnd*r.quantity,expires_at=now()+timedelta(minutes=30))
        db.add(p);db.commit()
        return dict(id=p.id,hash=p.proposal_hash,**payload)
