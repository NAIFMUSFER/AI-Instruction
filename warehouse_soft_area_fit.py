"""Fit provider-proposed soft warehouse room areas to a confirmed building target.
No regulatory dimensions are invented; confirmed role minima remain hard.
"""
from __future__ import annotations
import json, math
from acs_plan_review import PlanError, canonical


def _num(v): return type(v) in (int,float) and math.isfinite(v) and v >= 0

def _rooms(building):
    return [r for f in building.get('floors',{}).values() for r in f.get('rooms',[])]

def fit_soft_area(building, requirements, target):
    if not _num(target) or target <= 0: return building
    rooms=_rooms(building)
    if not rooms: return building
    areas={r['id']:r['rect'][2]*r['rect'][3] for r in rooms}
    before=math.fsum(areas.values())
    if before <= target + 1e-8*max(1,target): return building
    minima={}; source_ids={}
    for q in requirements or []:
        if not isinstance(q,dict) or q.get('metric')!='min_space_area_by_role_m2': continue
        role=q.get('role'); value=q.get('expected')
        if not isinstance(role,str) or not _num(value): continue
        key=role.strip().lower(); minima[key]=max(minima.get(key,0.0),float(value))
        source_ids.setdefault(key,[]).append(q.get('id'))
    current={}
    for r in rooms:
        role=str(r.get('role') or '').strip().lower(); current[role]=current.get(role,0.0)+areas[r['id']]
    hard=math.fsum(minima.values())
    if hard > target + 1e-8*max(1,target):
        raise PlanError('INFEASIBLE_HARD_PROGRAM','Confirmed warehouse role-area minima exceed the building target')
    weights={role:max(0.0,area-minima.get(role,0.0)) for role,area in current.items()}
    flex=math.fsum(weights.values()); remaining=target-hard
    if flex <= 0: raise PlanError('INFEASIBLE_HARD_PROGRAM','No soft warehouse area remains available for target fitting')
    role_targets={role:minima.get(role,0.0)+remaining*weights[role]/flex for role in current}
    out=json.loads(canonical(building))
    for r in _rooms(out):
        role=str(r.get('role') or '').strip().lower(); cur=current[role]
        if cur <= 0: continue
        scale=math.sqrt(role_targets[role]/cur)
        r['rect'][2]=round(r['rect'][2]*scale,4); r['rect'][3]=round(r['rect'][3]*scale,4)
    after=math.fsum(r['rect'][2]*r['rect'][3] for r in _rooms(out))
    diag=out.setdefault('meta',{}).setdefault('acs_stage_diagnostics',[])
    diag.append({'code':'WAREHOUSE_SOFT_AREA_FIT','before_m2':round(before,4),'after_m2':round(after,4),
                 'target_m2':float(target),'hard_minima_m2':round(hard,4),
                 'requirement_ids':sorted({i for ids in source_ids.values() for i in ids if isinstance(i,str)})})
    return out
