"""Conservative fresh-authoring context defaults, metres; never structural design.

Explicit role/flags only. Existing/imported models are not repaired. No renderer,
provider, storage or authentication dependency. Collision checks use every actual
box of the existing compiler's column/railing/plant/planter shapes, not nominal
object dimensions. Unsupported obstacles cause omission, not guessed clearances.
"""
import copy
import math

MARKER={'schema':'acs.context-details/1','source':'system_default','conceptual_only':True}
MAX_ADDED=12
MAX_ROOMS=512
MAX_OBJECTS=256
MAX_EXPANDED_PARTS=4096
EPS=1e-8


def _num(value):
    return type(value) in (int,float) and abs(value)<=1e12 and math.isfinite(value)


def _rect(value):
    return isinstance(value,list) and len(value)==4 and all(_num(v) for v in value) and value[2]>0 and value[3]>0


def _shape(model):
    if not isinstance(model,dict) or not isinstance(model.get('floors'),dict) or not isinstance(model.get('levels'),list):return False
    if 'meta' in model and not isinstance(model['meta'],dict):return False
    for floor in model['floors'].values():
        if not isinstance(floor,dict) or not isinstance(floor.get('rooms'),list):return False
        for room in floor['rooms']:
            if not isinstance(room,dict):return False
            for key in ('objects','doors','windows','lanes','racks','docks','stations'):
                if key in room and (not isinstance(room[key],list) or any(not isinstance(v,dict) for v in room[key])):return False
    return all(isinstance(level,dict) for level in model['levels'])


def _bounded(model):
    # Cheap iterative bound before copying. Equal cross-language conservative
    # numeric charge (32 bytes), not a claim of exact serialized JSON size.
    stack=[model];nodes=0;size=0
    while stack:
        value=stack.pop();nodes+=1
        if nodes>30000:return False
        if isinstance(value,dict):
            size+=2+len(value)*2
            for key,child in value.items():size+=len(str(key).encode('utf8'))*6+2;stack.append(child)
        elif isinstance(value,list):size+=2+len(value);stack.extend(value)
        elif isinstance(value,str):size+=len(value.encode('utf8'))*6+2
        elif value is None or isinstance(value,bool):size+=5
        elif _num(value):size+=32
        else:return False
        if size>600000:return False
    return True


def _parts(obj):
    if not isinstance(obj,dict) or obj.get('kind') not in ('column','railing','plant','planter','box'):raise ValueError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED')
    if any(not _num(obj.get(k)) for k in ('x','y','z','w','d','h','rot','pitch')):raise ValueError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED')
    w,d,h=obj['w'],obj['d'],obj['h']
    if min(w,d,h,obj['pitch'])<=0 or max(w,d,h)>1000 or type(obj.get('count')) is not int or not 1<=obj['count']<=200 or obj.get('dir') not in ('x','z'):raise ValueError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED')
    kind=obj['kind']
    if kind=='railing':
        n=max(2,round(w/1.1))
        if n>62:raise ValueError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED')
        return [(0,h,0,w,.06,.06)]+[(-w/2+w*i/n,h*.5,0,.05,h,.05) for i in range(n+1)]
    if kind=='plant':return [(0,.18,0,w*.55,.36,d*.55),(0,h*.62,0,w,h*.7,d)]
    return [(0,h*.5,0,w,h,d)]


def get_actual_bounds(obj):
    """Room-relative XYZ AABBs of every rotated/repeated actual compiler part.

    Bounds enclose each part after rotation (conservative for oblique angles).
    Includes x/y/z and count/pitch; no room origin or floor elevation added.
    """
    parts=_parts(obj);angle=math.radians(obj['rot']);co,sn=math.cos(angle),math.sin(angle);out=[]
    if len(parts)*obj['count']>1000:raise ValueError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED')
    for k in range(obj['count']):
        for dx,dy,dz,w,h,d in parts:
            cx=obj['x']+dx*co-dz*sn+(obj['pitch']*k if obj['dir']=='x' else 0)
            cz=obj['z']+dx*sn+dz*co+(obj['pitch']*k if obj['dir']=='z' else 0)
            hx=(abs(co)*w+abs(sn)*d)/2;hz=(abs(sn)*w+abs(co)*d)/2;cy=obj['y']+dy
            out.append({'min':[cx-hx,cy-h/2,cz-hz],'max':[cx+hx,cy+h/2,cz+hz]})
    return {'min':[min(p['min'][i] for p in out) for i in range(3)],'max':[max(p['max'][i] for p in out) for i in range(3)],'parts':out}


def _overlap(a,b,pad=0):
    return min(a[0]+a[2],b[0]+b[2]+pad)>max(a[0],b[0]-pad)+EPS and min(a[1]+a[3],b[1]+b[3]+pad)>max(a[1],b[1]-pad)+EPS


def _footprints(obj,room):
    return [[p['min'][0]+room['rect'][0],p['min'][2]+room['rect'][1],p['max'][0]-p['min'][0],p['max'][2]-p['min'][2]] for p in get_actual_bounds(obj)['parts']]


def _door_reservations(room):
    x,z,w,d=room['rect'];out=[]
    for door in room.get('doors',[]):
        edge=door.get('edge');offset=door.get('offset');width=door.get('width')
        if edge not in ('N','E','S','W') or not _num(offset) or not _num(width) or width<=0:raise ValueError('DOOR_GEOMETRY_UNKNOWN')
        length=w if edge in ('N','S') else d
        if offset-width/2<0 or offset+width/2>length:raise ValueError('DOOR_GEOMETRY_UNKNOWN')
        # Explicit authoring reservation: 1.2 m inward apron plus a conservative
        # rectangular door-to-centre route, not an accessibility/code claim.
        half=width/2+.2
        if edge in ('N','S'):
            zz=z if edge=='N' else z+d-1.2
            out.append([x+offset-half,zz,2*half,1.2])
            out.append([min(x+offset,x+w/2)-.6,min(zz,z+d/2)-.6,abs(offset-w/2)+1.2,abs(zz-z-d/2)+1.2])
        else:
            xx=x if edge=='W' else x+w-1.2
            out.append([xx,z+offset-half,1.2,2*half])
            out.append([min(xx,x+w/2)-.6,min(z+offset,z+d/2)-.6,abs(xx-x-w/2)+1.2,abs(offset-d/2)+1.2])
    return out


def _open_edge(room,edge,rooms):
    walls=room.get('walls')
    if walls=='none':walls=[]
    if not isinstance(walls,list) or any(v not in ('N','E','S','W') for v in walls):return False
    if edge in walls or any(d.get('edge')==edge for d in room.get('doors',[])):return False
    x,z,w,d=room['rect']
    for other in rooms:
        if other is room:continue
        a,b,c,e=other['rect']
        shared=(edge=='N' and abs(b+e-z)<EPS or edge=='S' and abs(b-z-d)<EPS) and min(x+w,a+c)>max(x,a)+EPS
        shared=shared or ((edge=='W' and abs(a+c-x)<EPS or edge=='E' and abs(a-x-w)<EPS) and min(z+d,b+e)>max(z,b)+EPS)
        if shared:return False
    return True


def _id(seed):
    # FNV-1a over UTF-8; fixed length and deterministic collision suffixes. This
    # identifies an authoring choice, not a cryptographic approval receipt.
    value=2166136261
    for byte in seed.encode('utf8'):value=((value^byte)*16777619)&0xffffffff
    return 'context_'+format(value,'08x')


def _provenance(context):
    return {'schema':'acs.context-detail/1','source':'system_default','conceptual_only':True,'context':context,
            'assumptions':['conceptual_dimensions','not_structurally_designed','door_route_reservation_1.2m','actual_component_bounds']}


def _valid_provenance(value):
    return (isinstance(value,dict) and set(value)=={'schema','source','conceptual_only','context','assumptions'}
            and value.get('schema')=='acs.context-detail/1' and value.get('source')=='system_default'
            and value.get('conceptual_only') is True and value.get('context') in ('porch','balcony','courtyard')
            and isinstance(value.get('assumptions'),list) and len(value['assumptions'])<=8
            and all(isinstance(v,str) and len(v)<=80 for v in value['assumptions']))


def list_context_details(model):
    if not _shape(model):return []
    out=[];scanned=0
    for level in model['levels'][:64]:
        template=level.get('template');floor=model['floors'].get(template) if isinstance(template,str) else None
        if not floor:continue
        for room in floor['rooms'][:MAX_ROOMS]:
            for obj in room.get('objects',[])[:MAX_OBJECTS]:
                scanned+=1
                if scanned>2048:return out
                if _valid_provenance(obj.get('context_detail_provenance')) and obj.get('kind') in ('column','railing','plant','planter') and isinstance(obj.get('id'),str):
                    out.append({'template':template,'level_index':level.get('index'),'room_id':room.get('id'),'element_id':obj['id'],'kind':obj['kind'],'count':obj.get('count'),'context_detail_provenance':copy.deepcopy(obj['context_detail_provenance'])})
                    if len(out)==MAX_OBJECTS:return out
    return out


def with_context_details(model):
    if not _shape(model):return model,None,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'
    report={'schema':'acs.context-details-report/1','conceptual_only':True,'added':[],'skipped':[]}
    existing=model.get('meta',{}).get('acs_context_details')
    if 'acs_context_details' in model.get('meta',{}):
        valid=isinstance(existing,dict) and existing==MARKER and existing.get('conceptual_only') is True
        return (model,report,None) if valid else (model,None,'CONTEXT_DETAILS_PROVENANCE_INVALID')
    try:
        bounded=_bounded(model)
    except UnicodeEncodeError:
        # Preserve canonical INVALID_JSON_VALUE handling; never replace malformed
        # Unicode or reinterpret it as a resource failure at this authoring layer.
        return model,None,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'
    if len(model['levels'])>64 or not bounded:return model,None,'CONTEXT_DETAILS_RESOURCE_LIMIT'
    floors=model['floors'];room_count=sum(len(f['rooms']) for f in floors.values());object_count=sum(len(r.get('objects',[])) for f in floors.values() for r in f['rooms'])
    if room_count>MAX_ROOMS or object_count>MAX_OBJECTS:return model,None,'CONTEXT_DETAILS_RESOURCE_LIMIT'
    for floor in floors.values():
        ids=[r.get('id') for r in floor['rooms']]
        if any(not isinstance(v,str) or not v.strip() for v in ids) or len(ids)!=len(set(ids)):return model,None,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'
    levels=model['levels'];uses={};indices=set()
    for level in levels:
        t=level.get('template');i=level.get('index')
        if not isinstance(t,str) or t not in floors or type(i) is not int or abs(i)>9007199254740991 or i in indices:return model,None,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'
        uses[t]=uses.get(t,0)+1;indices.add(i)
    # Unknown/legacy cores are reserved by room extent; validated physical U
    # connections additionally reserve exact incoming holes and arrival strips.
    reservations={}
    if any(o.get('form')=='u_return' for f in floors.values() for r in f['rooms'] for o in r.get('objects',[])):
        from acs_stairs import stair_connections
        try:
            for connection in stair_connections(model):
                for index in (connection['source_level_index'],connection['target_level_index']):reservations.setdefault(index,[]).extend([connection['opening'],connection['arrival']])
        except ValueError:return model,None,'CONTEXT_DETAILS_INPUT_UNSUPPORTED'
    planned=[];blocker_cache={};expanded_parts=0
    for level in levels:
        template=level['template'];rooms=floors[template]['rooms']
        if level.get('kind')=='roof':continue
        for room in rooms:
            role=room.get('role');context='porch' if role in ('porch','portico') else 'balcony' if role=='balcony' else 'courtyard' if role in ('courtyard','patio') else None
            if context is None:continue
            source={'template':template,'level_index':level['index'],'room_id':room.get('id')}
            def skip(reason):
                if len(report['skipped'])<128:report['skipped'].append(dict(source,reason=reason))
            if len(planned)>=MAX_ADDED:skip('ADDITION_LIMIT');continue
            if uses[template]!=1:skip('SHARED_TEMPLATE');continue
            if not isinstance(room.get('id'),str) or not room['id'].strip() or any(not _rect(r.get('rect')) for r in rooms):skip('ROOM_GEOMETRY_UNKNOWN');continue
            walls=room.get('walls')
            if walls!='none' and (not isinstance(walls,list) or any(v not in ('N','E','S','W') for v in walls)):skip('WALL_SEMANTICS_UNKNOWN');continue
            if context=='porch' and room.get('covered') is not True or context=='courtyard' and room.get('outdoor') is not True:skip('CONTEXT_UNCONFIRMED');continue
            wall=model.get('wall_t');height=room.get('wall_h',model.get('wall_h'))
            if not _num(wall) or wall<=0 or context=='porch' and (not _num(height) or height<=0 or height>1000):skip('DIMENSION_UNKNOWN');continue
            if any(other is not room and _overlap(room['rect'],other['rect']) for other in rooms):skip('ROOM_OVERLAP');continue
            index=level['index']
            if index not in blocker_cache:
                existing_blockers=list(reservations.get(index,[]));unknown=False
                try:
                    # Count cheap component descriptions before allocating any
                    # repeated bounds. Cache immutable existing blockers per
                    # physical level, including unsupported-obstacle results.
                    objects=[];prospective=0
                    for other in rooms:
                        for obj in other.get('objects',[]):
                            if obj.get('form')=='u_return':continue
                            parts=len(_parts(obj))*obj['count']
                            if parts>1000:raise ValueError('CONTEXT_DETAILS_BOUNDS_UNSUPPORTED')
                            prospective+=parts
                            if expanded_parts+prospective>MAX_EXPANDED_PARTS:return model,None,'CONTEXT_DETAILS_RESOURCE_LIMIT'
                            objects.append((obj,other))
                    for other in rooms:
                        existing_blockers.extend(_door_reservations(other))
                        if other.get('role') in ('stairs','stair','elevator','lift') or any(other.get(k) for k in ('lanes','racks','docks','stations')):existing_blockers.append(other['rect'])
                    for obj,other in objects:existing_blockers.extend(_footprints(obj,other))
                    expanded_parts+=prospective
                except ValueError:unknown=True
                blocker_cache[index]=(tuple(existing_blockers),unknown)
            cached,unknown=blocker_cache[index];blockers=list(cached)
            if unknown:skip('OBSTACLE_GEOMETRY_UNKNOWN');continue
            x,z,w,d=room['rect'];candidates=[];margin=wall/2+.15
            if context in ('porch','courtyard'):
                size=.45 if context=='porch' else .6;inset=margin+size/2
                if min(w,d)<2*inset+1.2:skip('INSUFFICIENT_SPACE');continue
                for px,pz in ((inset,inset),(w-inset,inset),(inset,d-inset),(w-inset,d-inset)):
                    candidates.append({'kind':'column' if context=='porch' else 'plant','x':px,'z':pz,'y':0,'w':size,'d':size,'h':height if context=='porch' else 1.2,'rot':0,'count':1,'pitch':1,'dir':'x'})
            else:
                for edge in ('N','E','S','W'):
                    if not _open_edge(room,edge,rooms):continue
                    span=(w if edge in ('N','S') else d)-2*margin-.05
                    if span<1.2 or span>50:continue
                    candidates.append({'kind':'railing','x':w/2 if edge in ('N','S') else (margin+.03 if edge=='W' else w-margin-.03),'z':d/2 if edge in ('E','W') else (margin+.03 if edge=='N' else d-margin-.03),'y':0,'w':span,'d':.06,'h':1.1,'rot':0 if edge in ('N','S') else 90,'count':1,'pitch':1,'dir':'x'})
            made=0;reserved_ids={v.get('id') for key,value in room.items() if isinstance(value,list) for v in value if isinstance(v,dict) and isinstance(v.get('id'),str)}
            for position,obj in enumerate(candidates):
                if made>=2 or len(planned)>=MAX_ADDED:break
                feet=_footprints(obj,room)
                if any(p[0]<x+margin-EPS or p[1]<z+margin-EPS or p[0]+p[2]>x+w-margin+EPS or p[1]+p[3]>z+d-margin+EPS or any(_overlap(p,b,.1) for b in blockers) for p in feet):continue
                base=_id(template+'\0'+str(level['index'])+'\0'+room['id']+'\0'+context+'\0'+str(position));identity=base;suffix=2
                while identity in reserved_ids:identity=base+'_'+str(suffix);suffix+=1
                reserved_ids.add(identity);obj['id']=identity;obj['context_detail_provenance']=_provenance(context)
                planned.append((template,room['id'],obj));report['added'].append(dict(source,element_id=identity,kind=obj['kind']));blockers.extend(feet);made+=1
            if not made:skip('NO_CLEAR_SUPPORTED_PLACEMENT')
    if not planned:return model,report,None
    out=copy.deepcopy(model)
    for template,rid,obj in planned:
        room=next(r for r in out['floors'][template]['rooms'] if r['id']==rid)
        room.setdefault('objects',[]).append(obj)
    out.setdefault('meta',{})['acs_context_details']=dict(MARKER)
    return out,report,None
