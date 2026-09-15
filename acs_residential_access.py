"""Geometric access from declared apartment entrances, not code certification.

Apartment interiors connect through their own rooms to common circulation.
Finished plans need aligned doors through both sides of a wall. Street access,
escape widths, accessibility and regulatory compliance are outside this check.
"""
from collections import defaultdict
import math

EPS = 0.0001
OPPOSITE = {'N':'S','S':'N','E':'W','W':'E'}

def scoped(building):
    return any(r.get('unit_id') and r.get('role') == 'bedroom'
               for f in building.get('floors',{}).values() for r in f.get('rooms',[]))

def edge(room, side):
    x,z,w,d=room['rect']
    return (z if side=='N' else z+d,x,x+w) if side in {'N','S'} else (x if side=='W' else x+w,z,z+d)

def wall(room,side):
    value=room.get('walls')
    return False if value=='none' else side in value if isinstance(value,list) else True

def portals(room,side):
    _,origin,_=edge(room,side);out=[]
    for o in room.get('doors',[]) or []:
        if not isinstance(o,dict) or o.get('edge')!=side:continue
        try:offset=float(o.get('offset',0));width=float(o.get('width',o.get('w',.9)))
        except (TypeError,ValueError):continue
        if math.isfinite(offset) and math.isfinite(width) and width>0:
            out.append((origin+offset-width/2,origin+offset+width/2))
    return out

def shared(a,b,doors):
    for side,other in OPPOSITE.items():
        line,lo,hi=edge(a,side);line2,lo2,hi2=edge(b,other)
        low,high=max(lo,lo2),min(hi,hi2)
        if abs(line-line2)>EPS or high-low<=EPS:continue
        if not doors:return True
        aa=portals(a,side) if wall(a,side) else [(low,high)]
        bb=portals(b,other) if wall(b,other) else [(low,high)]
        for p,q in aa:
            for r,s in bb:
                overlap=min(q,s,high)-max(p,r,low)
                if overlap>EPS and overlap>=min(q-p,s-r)-EPS:return True
    return False

def reachable(roots,allowed,graph):
    seen=set(roots)&allowed;pending=list(seen)
    while pending:
        for item in graph[pending.pop()]:
            if item in allowed and item not in seen:seen.add(item);pending.append(item)
    return seen

def issues(building,doors=True):
    if not scoped(building):return []
    out=[]
    for template,floor in building['floors'].items():
        rooms=floor['rooms'];by_id={r['id']:r for r in rooms};graph=defaultdict(set)
        def issue(rid,text):
            out.append({'code':'RESIDENTIAL_ACCESS_DISCONNECTED','room_ref':[template,rid],
                        'message':'['+template+'/'+rid+'] '+text,'severity':'error'})
        for i,a in enumerate(rooms):
            for b in rooms[i+1:]:
                if shared(a,b,doors):graph[a['id']].add(b['id']);graph[b['id']].add(a['id'])
        common={r['id'] for r in rooms if not r.get('unit_id')}
        ground=min((l['index'] for l in building['levels']),default=0)
        at_ground=any(l['index']==ground and l['template']==template for l in building['levels'])
        roots={r['id'] for r in rooms if r['id'] in common and r.get('role') in ({'entrance','lobby'} if at_ground else {'stairs','stair'})}
        if doors and at_ground:
            # A declared entrance needs an opening onto unoccupied exterior.
            roots={rid for rid in roots if any(
                not any(abs(edge(by_id[rid],side)[0]-edge(other,OPPOSITE[side])[0])<=EPS
                        and min(hi,edge(other,OPPOSITE[side])[2])-max(lo,edge(other,OPPOSITE[side])[1])>EPS
                        for other in rooms if other['id']!=rid)
                for side in OPPOSITE for lo,hi in portals(by_id[rid],side))}
        access=reachable(roots,common,graph)
        for rid in sorted(common-access):issue(rid,'اربط المدخل والممر المشترك والدرج والمصعد بمسار متصل'+(' وأبواب متقابلة متطابقة.' if doors else ' وحواف متلامسة.'))
        for unit in sorted({r.get('unit_id') for r in rooms if isinstance(r.get('unit_id'),str) and r['unit_id']}):
            own={r['id'] for r in rooms if r.get('unit_id')==unit}
            entries={rid for rid in own if by_id[rid].get('role') in {'corridor','entrance','living','majlis'} and graph[rid]&access}
            for rid in sorted(own-reachable(entries,own,graph)):
                issue(rid,'أكمل مسار الدخول من الممر المشترك إلى هذه الشقة ثم غرفها، دون المرور بشقة أخرى'+('؛ يجب أن تتقابل الأبواب على الجدار المشترك.' if doors else '.'))
    return out[:128]

def opening_collisions(building):
    """Doors and windows share a wall; compare both height and wall position."""
    out=[]
    if not scoped(building):return out
    for template,floor in building['floors'].items():
        for room in floor['rooms']:
            for door in room.get('doors',[]) or []:
                for window in room.get('windows',[]) or []:
                    if door.get('edge')!=window.get('edge'):continue
                    try:
                        center=float(door['offset']);width=float(door.get('width',door.get('w')))
                        wc=float(window['offset']);ww=float(window.get('width',window.get('w')))
                        top=float(door.get('height',door.get('h')))
                        sill=float(window.get('sill',0));height=float(window.get('height',window.get('h')))
                    except (TypeError,ValueError,KeyError):continue
                    if (min(center+width/2,wc+ww/2)-max(center-width/2,wc-ww/2)>EPS
                            and min(top,sill+height)-max(0,sill)>EPS):
                        out.append({'code':'RESIDENTIAL_OPENING_COLLISION','room_ref':[template,room['id']],
                                    'severity':'error','message':'['+template+'/'+room['id']+'] باب ونافذة متداخلان على الحافة '+str(door['edge'])+'؛ باعد بين الفتحتين.'})
    return out[:128]

def detail_issues(building):
    import acs_validate as V
    findings,_=V.validate_building(building)
    return ([{'code':'ACS_GEOMETRY_FINDING','message':str(x)} for x in findings]
            + issues(building) + opening_collisions(building))[:128]
