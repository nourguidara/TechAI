"""Deterministic resource-based suitability estimates, never benchmark scores."""
from decimal import Decimal
from backend.schemas import Requirements

VERSION = 'resource-fit-v1'
# Relative weights; the sum is normalized at scoring time. No implicit hard requirements.
BASE = dict(ram=20, storage=15, ssd=10, processor_information=5, completeness=15,
            headroom=15, value=15, brand_preference=5)
PROFILES = {
    'programming': dict(ram=40, storage=15, ssd=15, headroom=5, value=5),
    'machine_learning': dict(ram=45, storage=25, ssd=10, headroom=5, value=5),
    'gaming': dict(ram=15, storage=40, ssd=15, headroom=5, value=5),
    'video_editing': dict(ram=35, storage=35, ssd=15, headroom=5, value=5),
    'study': dict(ram=15, storage=10, headroom=35, value=25),
    'notes': dict(ram=10, storage=10, completeness=20, headroom=40, value=20),
    'media': dict(ram=10, storage=20, headroom=30, value=25),
}
PRIORITY = {'ram':'ram','storage':'storage','value':'value',
            'budget_headroom':'headroom','data_confidence':'completeness'}
CORE = ('brand','processor','ram_gb','storage_gb','storage_type','operating_system')

def score(offer: dict, requirements: Requirements) -> dict:
    profiles = [BASE | PROFILES.get(use,{}) for use in (requirements.intended_use or ['general'])]
    weights = {key: sum(p[key] for p in profiles)/len(profiles) for key in BASE}
    for priority in set(requirements.priorities):
        if priority in PRIORITY: weights[PRIORITY[priority]] += 20
    total = Decimal(offer['price_tnd']) * requirements.quantity
    fraction = float(total / requirements.budget)
    ram = min(max(offer['ram_gb'] or 0,0)/32,1)
    storage = min(max(offer['storage_gb'] or 0,0)/1024,1)
    ssd = float(offer['storage_type']=='SSD')
    completeness = sum(offer[k] is not None for k in CORE)/len(CORE)
    preferred = [b.casefold() for b in requirements.preferred_brands]
    values = dict(ram=ram, storage=storage, ssd=ssd,
        processor_information=float(bool(offer['processor'])), completeness=completeness,
        headroom=max(0,1-fraction), value=min(((ram+storage+ssd)/3)/max(fraction,.001),2)/2,
        brand_preference=float(bool(preferred) and (offer['brand'] or '').casefold() in preferred))
    if not preferred: weights['brand_preference']=0
    components = {key: round(100*weights[key]*values[key]/sum(weights.values()),3) for key in weights}
    facts = [f"Unit price {offer['price_tnd']} TND; merchandise total {total:.3f} TND."]
    for key,label in [('ram_gb','RAM (GB)'),('storage_gb','Storage (GB)'),('storage_type','Storage type'),('processor','Processor as listed')]:
        if offer[key] is not None: facts.append(f'{label}: {offer[key]}')
    missing = [k.replace('_',' ') for k in CORE if offer[k] is None]
    limitations = ['Estimated suitability from listed specifications; not a performance benchmark.']
    if missing: limitations.append('Unknown specifications: '+', '.join(missing)+'. Unknown values earn no positive credit.')
    uses=set(requirements.intended_use)
    if uses & {'gaming','machine_learning','video_editing'} or 'graphics' in requirements.priorities:
        limitations.append('GPU/VRAM and benchmarks are not collected. Modern-game performance, ML acceleration and editing speed cannot be confirmed.')
    if 'notes' in uses:
        limitations.append('Stylus support, pen compatibility and note-taking app support are unverified.')
    if 'portability' in requirements.priorities:
        limitations.append('Weight is unknown. Portability is not inferred from screen size.')
    if 'battery' in requirements.priorities or 'study' in uses:
        limitations.append('Battery life and weight are unverified; university portability is not established.')
    if requirements.soft_preferences:
        limitations.append('Free-text soft preferences are not individually verified: '+'; '.join(requirements.soft_preferences))
    reason = ('Estimated fit for '+', '.join(requirements.intended_use or ['general use'])+
        ': weights favor '+', '.join(sorted(weights,key=weights.get,reverse=True)[:3])+'. '
        'Only listed specifications contribute; processor presence earns information credit, not a speed rating.')
    return dict(**offer, total_tnd=f'{total:.3f}', remaining_budget_tnd=f'{requirements.budget-total:.3f}',
        ranking_reason=reason,stock_note='Exact quantity not published; sandbox order only.' if offer['available_quantity'] is None else 'Published quantity is sufficient.',
        label='',suitability_score=round(sum(components.values()),3),score_components=components,
        facts=facts,limitations=limitations,tradeoffs=[],scoring_version=VERSION)

def rank(offers: list[dict], requirements: Requirements) -> list[dict]:
    scored=[score(o,requirements) for o in offers]
    scored.sort(key=lambda o:(-o['suitability_score'],Decimal(o['price_tnd']),o['id']))
    if not scored: return []
    best=scored[0]; best['label']='Best Overall Recommendation'
    result=[best]
    for other in scored[1:]:
        tradeoffs=[]; labels=[]
        if Decimal(other['price_tnd']) < Decimal(best['price_tnd']):
            labels.append('Lower Price'); tradeoffs.append('Lower merchandise price than the best overall recommendation.')
        elif Decimal(other['price_tnd']) > Decimal(best['price_tnd']):
            tradeoffs.append('Costs more and leaves less budget than the best overall recommendation.')
        for field,label in [('ram_gb','memory'),('storage_gb','storage')]:
            a,b=other[field],best[field]
            if a is not None and b is not None and a>b:
                labels.append('More '+label); tradeoffs.append(f'More listed {label}: {a} GB versus {b} GB.')
            elif a is not None and b is not None and a<b:
                tradeoffs.append(f'Less listed {label}: {a} GB versus {b} GB.')
        if other['supplier']!=best['supplier']: labels.append('Different Retailer')
        if other['brand'] and other['brand']!=best['brand']: labels.append('Different Brand')
        if other['processor'] and other['processor']!=best['processor']:
            labels.append('Different Processor'); tradeoffs.append('Different listed processor; relative performance is unverified.')
        if sum(other[k] is not None for k in CORE)>sum(best[k] is not None for k in CORE):
            labels.append('More Complete Specifications')
        if not labels: continue  # Omit indistinguishable/dominated duplicate alternatives.
        other['label']=labels[0]; other['tradeoffs']=tradeoffs or ['Different retailer or brand; compare the listed facts and source.']
        result.append(other)
        if len(result)==4: break
    return result
