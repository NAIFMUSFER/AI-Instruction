"""Explicit conceptual U stairs. Pure canonical authoring and geometry, never a renderer repair.

Only fresh-generation callers may author defaults. Imported/approved models are
read without modification. Components do not certify support, guards, headroom,
accessibility, fire escape, or a traversable navigation path.
"""
import copy
import hashlib
import json
import math

EPS = 1e-6
SCHEMA = 'acs.stairs/1'
# A bounded default-authoring profile, deliberately below canonical admission's
# 900 kB/50k nodes. These do not redefine the limits for imported/authored models.
MAX_DEFAULT_CONNECTIONS = 128
MAX_DEFAULT_ROOM_INSTANCES = 512
MAX_DEFAULT_BYTES = 600_000
MAX_DEFAULT_NODES = 30_000


def _shape_valid(model):
    if not isinstance(model,dict) or not isinstance(model.get('floors'),dict) or not isinstance(model.get('levels'),list):
        return False
    if 'meta' in model and not isinstance(model['meta'],dict):
        return False
    for floor in model['floors'].values():
        if not isinstance(floor,dict) or not isinstance(floor.get('rooms'),list):
            return False
        for room in floor['rooms']:
            if not isinstance(room,dict) or ('objects' in room and (not isinstance(room['objects'],list) or any(not isinstance(o,dict) for o in room['objects']))):
                return False
    return all(isinstance(level,dict) for level in model['levels'])


def _stair_object(obj):
    return isinstance(obj,dict) and any(word in str(obj.get('kind') or obj.get('name') or '').lower()
                                        for word in ('stair','درج','سلم'))


def _validate_forms(model):
    for floor in model['floors'].values():
        for room in floor['rooms']:
            for obj in room.get('objects',[]):
                if _stair_object(obj) and 'form' in obj and obj['form']!='u_return':
                    raise ValueError('STAIR_FORM_UNSUPPORTED')


def _number(v):
    try:
        return type(v) in (int, float) and math.isfinite(v)
    except (OverflowError, ValueError):
        return False


def _q(v):
    return round(v, 6)


def _id(value):
    text = str(value)
    return text if len(text) <= 160 else text[:139] + '_' + hashlib.sha256(text.encode()).hexdigest()[:20]


def _elevation(level, model):
    if type(level.get('index')) is not int:
        raise ValueError('STAIR_LEVEL_INVALID')
    try:
        v = level.get('elevation') if 'elevation' in level else (
            level['index'] * model['floor_height'] if _number(model.get('floor_height')) else None)
    except OverflowError:
        raise ValueError('STAIR_ELEVATION_INVALID') from None
    if not _number(v):
        raise ValueError('STAIR_ELEVATION_NOT_SPECIFIED')
    return v


def _levels(model):
    raw = model.get('levels')
    if not isinstance(raw, list) or len(raw) > 64:
        raise ValueError('STAIR_LEVEL_INVALID')
    levels = []
    seen = set()
    for l in raw:
        if (not isinstance(l, dict) or not isinstance(l.get('template'),str) or
            type(l.get('index')) is not int or abs(l['index'])>9007199254740991 or
            l.get('template') not in model.get('floors', {})):
            raise ValueError('STAIR_LEVEL_INVALID')
        if l.get('index') in seen:
            raise ValueError('STAIR_LEVEL_INVALID')
        seen.add(l.get('index'))
        if l.get('kind') != 'roof':
            levels.append((l, _elevation(l, model)))
    levels.sort(key=lambda v: (v[1], v[0]['index']))
    if any(abs(a[1]-b[1]) < EPS for a,b in zip(levels, levels[1:])):
        raise ValueError('STAIR_LEVEL_ELEVATION_AMBIGUOUS')
    return levels


def resolve_stair_geometry(obj):
    """Return local unrotated boxes and rectangles from fully stated geometry.

    N risers per flight have N-1 treads; the intermediate landing and destination
    slab supply the final rise of their respective flights. Positive rotation
    subsequently maps +X toward +Z, matching the canonical compiler convention.
    """
    if not isinstance(obj, dict) or obj.get('kind') != 'stairs' or obj.get('form') != 'u_return':
        raise ValueError('STAIR_FORM_UNSUPPORTED')
    if not isinstance(obj.get('id'),str) or not obj['id'].strip() or len(obj['id'])>160:
        raise ValueError('STAIR_ID_NOT_SPECIFIED')
    s = obj.get('stair')
    if not isinstance(s, dict) or s.get('schema') != 'acs.stair/1':
        raise ValueError('STAIR_GEOMETRY_NOT_SPECIFIED')
    fields = ('flight_width_m','gap_m','tread_m','entry_landing_m','mid_landing_m','landing_thickness_m')
    if any(not _number(s.get(k)) or s[k] <= 0 for k in fields):
        raise ValueError('STAIR_GEOMETRY_INVALID')
    if any(not _number(obj.get(k)) for k in ('x','y','z','w','d','h','rot')):
        raise ValueError('STAIR_GEOMETRY_NOT_SPECIFIED')
    if obj['rot'] % 90 != 0:
        raise ValueError('STAIR_ROTATION_UNSUPPORTED')
    n = s.get('risers_per_flight')
    if type(n) is not int or not 2 <= n <= 32:
        raise ValueError('STAIR_RISER_COUNT_INVALID')
    if obj.get('count') != 1 or type(obj.get('count')) is not int or obj.get('dir') != 'x' or obj.get('pitch') != 1:
        raise ValueError('STAIR_REPETITION_UNSUPPORTED')
    if any(type(s.get(k)) is not int for k in ('source_level_index','target_level_index')):
        raise ValueError('STAIR_CONNECTION_NOT_SPECIFIED')
    if any(not _number(s.get(k)) for k in ('source_elevation_m','target_elevation_m')):
        raise ValueError('STAIR_CONNECTION_NOT_SPECIFIED')
    h = s['target_elevation_m'] - s['source_elevation_m']
    fw,gap,tread,entry,mid,thick = (s[k] for k in fields)
    w, d = 2*fw+gap, entry+(n-1)*tread+mid
    if h <= 0 or obj['y'] != 0 or h/2 < thick or any(abs(a-b)>EPS for a,b in ((obj['h'],h),(obj['w'],w),(obj['d'],d))):
        raise ValueError('STAIR_DIMENSION_MISMATCH')
    rise = h/(2*n); start=-d/2+entry; run=(n-1)*tread
    components=[]
    for flight in (1,2):
        for i in range(1,n):
            top = i*rise if flight==1 else h/2+i*rise
            z = start+(i-.5)*tread if flight==1 else start+run-(i-.5)*tread
            components.append({'id': 'f%d_t%02d'%(flight,i), 'role':'tread',
                'center': [_q((-(fw+gap)/2) if flight==1 else (fw+gap)/2), _q(top-rise/2), _q(z)],
                'size': [_q(fw),_q(rise),_q(tread)]})
    components.append({'id':'mid_landing','role':'mid_landing',
        'center':[0,_q(h/2-thick/2),_q(d/2-mid/2)],'size':[_q(w),_q(thick),_q(mid)]})
    return {'components':components, 'opening':[_q(-w/2),_q(start),_q(w),_q(d-entry)],
            'arrival':[_q(-w/2),_q(-d/2),_q(w),_q(entry)]}


def _world_rect(rect, obj, room):
    x,z,w,d=rect; turns=int(obj['rot']/90)%4
    def turn(a,b):
        return ((a,b),(-b,a),(-a,-b),(b,-a))[turns]
    points=[turn(a,b) for a,b in ((x,z),(x+w,z),(x+w,z+d),(x,z+d))]
    xs=[p[0]+room['rect'][0]+obj['x'] for p in points]
    zs=[p[1]+room['rect'][1]+obj['z'] for p in points]
    return [_q(min(xs)),_q(min(zs)),_q(max(xs)-min(xs)),_q(max(zs)-min(zs))]


def stair_connections(model):
    """Validate all U connections against current physical instances; never repair."""
    if not _shape_valid(model):
        raise ValueError('STAIR_MODEL_INVALID')
    _validate_forms(model)
    if not has_u_stairs(model):
        return []
    template_scope_aliases(model)
    for level in model.get('levels',[]):
        if isinstance(level,dict) and level.get('kind')=='roof':
            floor=model.get('floors',{}).get(level.get('template'),{})
            if any(isinstance(o,dict) and o.get('form')=='u_return' for r in floor.get('rooms',[]) for o in (r.get('objects') or [])):
                raise ValueError('STAIR_ROOF_ACCESS_UNSUPPORTED')
    levels=_levels(model); by_index={l['index']:(l,e) for l,e in levels}; out=[]
    for position,(level,elev) in enumerate(levels):
        for room in model['floors'][level['template']].get('rooms',[]):
            for obj in room.get('objects',[]) or []:
                if not isinstance(obj,dict) or obj.get('form') != 'u_return':
                    continue
                geometry=resolve_stair_geometry(obj); s=obj['stair']
                target=by_index.get(s['target_level_index'])
                if (s['source_level_index']!=level['index'] or abs(s['source_elevation_m']-elev)>EPS or
                    target is None or abs(target[1]-s['target_elevation_m'])>EPS or
                    position+1>=len(levels) or levels[position+1][0]['index']!=target[0]['index']):
                    raise ValueError('STAIR_CONNECTION_STALE')
                candidates=[r for r in model['floors'][target[0]['template']].get('rooms',[])
                            if r.get('core_id') and r.get('core_id')==room.get('core_id') and r.get('role') in ('stair','stairs')]
                if len(candidates)!=1 or candidates[0].get('rect')!=room.get('rect'):
                    raise ValueError('STAIR_CORE_ALIGNMENT_CHANGED')
                rc=room.get('rect'); wall=model.get('wall_t')
                if not isinstance(rc,list) or len(rc)!=4 or any(not _number(v) for v in rc) or not _number(wall) or wall<=0:
                    raise ValueError('STAIR_CORE_DIMENSION_NOT_SPECIFIED')
                box=_world_rect([-obj['w']/2,-obj['d']/2,obj['w'],obj['d']],obj,room)
                if box[0]<rc[0]+wall/2-EPS or box[1]<rc[1]+wall/2-EPS or box[0]+box[2]>rc[0]+rc[2]-wall/2+EPS or box[1]+box[3]>rc[1]+rc[3]-wall/2+EPS:
                    raise ValueError('STAIR_CORE_TOO_SMALL')
                arrival=_world_rect(geometry['arrival'],obj,room)
                if not all(_entry_matches(r,arrival,obj['rot'],wall) for r in (room,candidates[0])):
                    raise ValueError('STAIR_ENTRY_CHANGED')
                out.append({'source_level_index':level['index'],'target_level_index':target[0]['index'],
                    'room_id':room.get('id'),'target_room_id':candidates[0].get('id'),
                    'core_id':room.get('core_id'),'source_object_id':obj.get('id'), 'object':obj,
                    'opening':_world_rect(geometry['opening'],obj,room),
                    'arrival':arrival})
    return out


def _entry_matches(room, arrival, rotation, wall):
    doors=room.get('doors') or []
    if len(doors)!=1 or not isinstance(doors[0],dict):
        return False
    door=doors[0]; edge=('N','E','S','W')[int(rotation/90)%4]
    if door.get('edge')!=edge or not _number(door.get('offset')) or not _number(door.get('width')) or door['width']<=0:
        return False
    x,z,w,d=room['rect']; ax,az,aw,ad=arrival
    fixed={'N':(az,z+wall/2),'S':(az+ad,z+d-wall/2),
           'E':(ax+aw,x+w-wall/2),'W':(ax,x+wall/2)}[edge]
    if abs(fixed[0]-fixed[1])>EPS:
        return False
    center=(x if edge in ('N','S') else z)+door['offset']
    a0,a1=(ax,ax+aw) if edge in ('N','S') else (az,az+ad)
    return center-door['width']/2>=a0-EPS and center+door['width']/2<=a1+EPS


def _cores(model, level):
    rooms=model['floors'][level['template']].get('rooms',[])
    return [r for r in rooms if r.get('role') in ('stair','stairs')]


def has_u_stairs(model):
    if not _shape_valid(model):
        return False
    return any(isinstance(o,dict) and o.get('form')=='u_return'
               for f in model.get('floors',{}).values() if isinstance(f,dict)
               for r in f.get('rooms',[]) if isinstance(r,dict)
               for o in (r.get('objects') or []))


def has_stair_forms(model):
    """Narrow new-feature admission; legacy diagnostic rendering stays unchanged."""
    floors=model.get('floors') if isinstance(model,dict) else None
    if not isinstance(floors,dict):
        return False
    for floor in floors.values():
        rooms=floor.get('rooms') if isinstance(floor,dict) else None
        for room in rooms if isinstance(rooms,list) else []:
            objects=room.get('objects') if isinstance(room,dict) else None
            for obj in objects if isinstance(objects,list) else []:
                if isinstance(obj,dict) and (obj.get('form')=='u_return' or (_stair_object(obj) and 'form' in obj)):
                    return True
    return False


def _uses_stair_contract(model):
    """Select stair-specific admission without replacing generic provenance.

    A malformed non-stair collection still belongs to the established handoff
    provenance boundary. Explicit stair declarations remain strict even inside
    an incorrectly shaped collection; this detector never legitimizes it.
    """
    if not isinstance(model,dict):return False
    meta=model.get('meta')
    if isinstance(meta,dict) and 'acs_stairs' in meta:return True
    levels=model.get('levels')
    if isinstance(levels,list) and any(isinstance(level,dict) and
        ('stair_source_template' in level or 'stair_template_instance' in level) for level in levels):
        return True
    floors=model.get('floors')
    if not isinstance(floors,dict):return False
    for floor in floors.values():
        rooms=floor.get('rooms') if isinstance(floor,dict) else None
        for room in rooms if isinstance(rooms,list) else []:
            objects=room.get('objects') if isinstance(room,dict) else None
            if isinstance(objects,list):candidates=objects
            elif isinstance(objects,dict):candidates=[objects,*objects.values()]
            else:continue
            for obj in candidates:
                if isinstance(obj,dict) and ('stair_provenance' in obj or obj.get('form')=='u_return' or
                    (_stair_object(obj) and 'form' in obj)):
                    return True
    return False


def template_scope_aliases(model):
    """Validate canonical instance scope, never accept a bare lineage label.

    This is a declared canonical scope relationship, not an attestation of who
    authored a model. Provider-generated system metadata is rejected separately
    at the fresh-generation boundary. Locks bind these records with the model.
    """
    result={}; levels=model.get('levels') or []; floors=model.get('floors') or {}
    for level in levels:
        if not isinstance(level,dict) or not ({'stair_source_template','stair_template_instance'} & set(level)):
            continue
        source=level.get('stair_source_template'); template=level.get('template'); record=level.get('stair_template_instance')
        if (not isinstance(source,str) or not source.strip() or len(source)>160 or source not in floors or
            not isinstance(template,str) or template not in floors or source==template or not isinstance(record,dict) or
            record.get('schema')!='acs.stair-template-instance/1' or record.get('source_template')!=source or
            record.get('template')!=template or type(record.get('level_index')) is not int or record.get('level_index')!=level.get('index') or
            sum(l.get('template')==template for l in levels if isinstance(l,dict))!=1 or
            not any(l.get('template')==source and 'stair_source_template' not in l for l in levels if isinstance(l,dict))):
            raise ValueError('STAIR_TEMPLATE_SCOPE_INVALID')
        def mapping(key):
            return [{'id':r.get('id'),'role':r.get('role')} for r in floors[key].get('rooms',[])]
        original=mapping(source); variant=mapping(template)
        if (not original or any(not isinstance(r['id'],str) or not r['id'].strip() or len(r['id'])>160 for r in original) or
            len({r['id'] for r in original})!=len(original) or original!=variant or original!=record.get('room_mapping')):
            raise ValueError('STAIR_TEMPLATE_SCOPE_CHANGED')
        result.setdefault(template,set()).add(source)
    return result


def validate_stair_report(model):
    meta=model.get('meta')
    if not isinstance(meta,dict) or 'acs_stairs' not in meta:
        return
    report=meta['acs_stairs']; connections=stair_connections(model)
    if any(not isinstance(c['object'].get('stair_provenance',{}),dict) for c in connections):
        raise ValueError('STAIR_PROVENANCE_INVALID')
    generated=sum(c['object'].get('stair_provenance',{}).get('source')=='system_default' for c in connections)
    if (not isinstance(report,dict) or report.get('schema')!=SCHEMA or report.get('source')!='system_default' or
        report.get('physical_traversal')!='NOT_VERIFIED' or type(report.get('generated_connections')) is not int or
        report['generated_connections']!=generated or not isinstance(report.get('unsupported'),list)):
        raise ValueError('STAIR_REPORT_INVALID')


def _resource_limited(model, levels):
    """Conservative prospective output admission before core searches or cloning."""
    physical_rooms=sum(len(model['floors'][l['template']]['rooms']) for l,_ in levels)
    cores=sum(r.get('role') in ('stair','stairs') for r in model['floors'][levels[0][0]['template']]['rooms'])
    prospective=cores*(len(levels)-1)
    if prospective==0:
        return False
    if physical_rooms>MAX_DEFAULT_ROOM_INSTANCES or prospective>MAX_DEFAULT_CONNECTIONS:
        return True
    # Bound traversal and scalar encoding before serializing even the input.
    nodes=0;text_size=0;stack=[(model,0)]
    while stack:
        value,depth=stack.pop();nodes+=1
        if nodes>MAX_DEFAULT_NODES or depth>32:
            return True
        if isinstance(value,(dict,list)):
            if nodes+len(stack)+len(value)>MAX_DEFAULT_NODES:
                return True
            if isinstance(value,dict):
                for key in value:
                    if not isinstance(key,str):return True
                    text_size+=len(key)
                stack.extend((v,depth+1) for v in value.values())
            else:stack.extend((v,depth+1) for v in value)
        elif isinstance(value,str):text_size+=len(value)
        elif type(value) in (int,float) and (not _number(value) or abs(value)>9007199254740991):return True
        elif value is not None and type(value) not in (int,float,bool):return True
        if text_size>MAX_DEFAULT_BYTES:return True
    # Native Python and JS serializers disagree about e.g.1.0 versus1. Charge
    # each finite safe-range number32bytes instead: a shared conservative upper
    # bound, with exact UTF8 JSON string and punctuation costs. This is admission
    # accounting only; no canonical number is converted or rounded.
    weights={}
    def weight(value):
        if isinstance(value,dict):
            size=2+max(0,len(value)-1);count=1
            for key,child in value.items():
                b,n=weight(child);size+=len(json.dumps(key,ensure_ascii=False).encode('utf-8'))+1+b;count+=n
            weights[id(value)]=(size,count)
            return size,count
        if isinstance(value,list):
            children=[weight(child) for child in value]
            result=(2+max(0,len(value)-1)+sum(b for b,_ in children),1+sum(n for _,n in children))
            weights[id(value)]=result
            return result
        if value is None:return 4,1
        if type(value) is bool:return (4 if value else 5),1
        if type(value) in (int,float):return 32,1
        return len(json.dumps(value,ensure_ascii=False).encode('utf-8')),1
    try:
        size,nodes=weight(model)
    except (ValueError,OverflowError,UnicodeError,RecursionError):
        return True
    # Every repeated occupied template is conservatively treated as requiring
    # variants. A floor copy plus its identity map is bounded by two copies;
    # 2048 bytes/32 nodes allow the instance record and bounded template ID.
    counts={}
    for level,_ in levels:counts[level['template']]=counts.get(level['template'],0)+1
    preserve={l['template'] for l in model['levels'] if l.get('kind')=='roof'}
    for template,count in counts.items():
        extra=max(0,count-(0 if template in preserve else 1))
        if not extra:continue
        floor=model['floors'][template]
        floor_bytes,floor_nodes=weights[id(floor)]
        size+=extra*(2*floor_bytes+2048);nodes+=extra*(2*floor_nodes+32)
    # New objects have bounded IDs and fixed numeric fields. This deliberately
    # overestimates both objects and report rows, including optional provenance.
    size+=prospective*4096+2048;nodes+=prospective*96+64
    return size>MAX_DEFAULT_BYTES or nodes>MAX_DEFAULT_NODES


def with_default_stairs(model):
    """Author defaults only at a fresh-generation boundary; return (model, report, reason).

    Whole core chains are admitted together so unsupported intermediate geometry
    cannot leave a falsely continuous connection. Authored objects are retained.
    """
    if not _shape_valid(model):
        return model,None,'STAIR_MODEL_INVALID'
    try:
        _validate_forms(model)
    except ValueError as exc:
        return model,None,str(exc)
    if isinstance(model.get('meta'),dict) and 'acs_stairs' in model['meta']:
        try:
            validate_stair_report(model)
            return model,model['meta']['acs_stairs'],None
        except ValueError as exc:
            return model,None,str(exc)
    try:
        levels=_levels(model)
    except ValueError as exc:
        return model,None,str(exc)
    report={'schema':SCHEMA,'source':'system_default','generated_connections':0,'unsupported':[],
            'physical_traversal':'NOT_VERIFIED',
            'not_verified':['structure','guards','headroom','accessibility','fire escape','code compliance']}
    if len(levels)<2:
        return model,report,'STAIR_NOT_APPLICABLE'
    if _resource_limited(model,levels):
        report['unsupported']=[{'code':'STAIR_RESOURCE_LIMIT'}]
        # No allocation of a new model and no claimed provenance is attached.
        # Fresh-generation callers must reject this result before publication.
        return model,report,'STAIR_RESOURCE_LIMIT'
    first_cores=_cores(model,levels[0][0]); plans=[]
    for first in first_cores:
        core=first.get('core_id'); code=None; chain=[]
        if not isinstance(core,str) or not core.strip() or len(core)>160:
            code='STAIR_CORE_ID_NOT_SPECIFIED'
        for level,elev in levels:
            candidates=[r for r in _cores(model,level) if r.get('core_id')==core]
            if len(candidates)!=1:
                code=code or 'STAIR_CORE_ALIGNMENT_CHANGED';break
            room=candidates[0]; chain.append((level,elev,room))
            if room.get('rect') != first.get('rect'):
                code=code or 'STAIR_CORE_ALIGNMENT_CHANGED'
            if any(isinstance(o,dict) and (o.get('form')=='u_return' or _stair_object(o))
                for o in (room.get('objects') or [])):
                code=code or 'STAIR_AUTHORED_GEOMETRY_PRESERVED'
        proposed=[]
        if not code:
            for (level,elev,room),(target,target_elev,_) in zip(chain,chain[1:]):
                rc=room.get('rect'); wall=model.get('wall_t')
                if not isinstance(rc,list) or len(rc)!=4 or any(not _number(v) for v in rc) or not _number(wall) or wall<=0:
                    code='STAIR_CORE_DIMENSION_NOT_SPECIFIED';break
                doors=room.get('doors') or []
                edges={d.get('edge') for d in doors if isinstance(d,dict)}
                if len(edges)!=1 or len(doors)!=1 or next(iter(edges),None) not in ('N','E','S','W'):
                    code='STAIR_ENTRY_UNSUPPORTED';break
                door=doors[0]; edge=door['edge']; rot={'N':0,'E':90,'S':180,'W':270}[edge]
                # Explicit conceptual profile, not a code-derived dimension.
                h=target_elev-elev
                if not 2.4-EPS<=h<=3.6+EPS:
                    code='STAIR_DEFAULT_RISE_UNSUPPORTED';break
                w,d=1.9,3.8; fw,fd=(w,d) if rot%180==0 else (d,w)
                if rc[2]<fw+wall-EPS or rc[3]<fd+wall-EPS:
                    code='STAIR_CORE_TOO_SMALL';break
                offset=door.get('offset'); width=door.get('width')
                if not _number(offset) or not _number(width) or width<=0 or width>w:
                    code='STAIR_ENTRY_UNSUPPORTED';break
                # Centre the entry strip on the actual door, placing its outer
                # edge at the internal wall face. No room dimension is changed.
                x=offset if edge in ('N','S') else (wall/2+d/2 if edge=='W' else rc[2]-wall/2-d/2)
                z=offset if edge in ('E','W') else (wall/2+d/2 if edge=='N' else rc[3]-wall/2-d/2)
                if x-fw/2<wall/2-EPS or x+fw/2>rc[2]-wall/2+EPS or z-fd/2<wall/2-EPS or z+fd/2>rc[3]-wall/2+EPS:
                    code='STAIR_ENTRY_UNSUPPORTED';break
                base=_id('stairs_'+core+'_'+str(level['index'])+'_'+str(target['index']))
                used_ids={item.get('id') for values in room.values() if isinstance(values,list)
                          for item in values if isinstance(item,dict) and isinstance(item.get('id'),str)}
                object_id=base;n=2
                while object_id in used_ids:
                    suffix='_'+str(n);object_id=base[:160-len(suffix)]+suffix;n+=1
                obj={'id':object_id,
                     'kind':'stairs','form':'u_return','x':_q(x),'z':_q(z),'y':0,'w':w,'d':d,'h':_q(h),
                     'rot':rot,'count':1,'pitch':1,'dir':'x',
                     'stair':{'schema':'acs.stair/1','source_level_index':level['index'],'target_level_index':target['index'],
                         'source_elevation_m':elev,'target_elevation_m':target_elev,'flight_width_m':.9,'gap_m':.1,
                         'tread_m':.25,'risers_per_flight':9,'entry_landing_m':.9,'mid_landing_m':.9,'landing_thickness_m':.15},
                     'stair_provenance':{'source':'system_default','source_room_id':room.get('id'),'core_id':core}}
                geometry=resolve_stair_geometry(obj)
                arrival=_world_rect(geometry['arrival'],obj,room)
                target_room=next(r for r in _cores(model,target) if r.get('core_id')==core)
                if not _entry_matches(target_room,arrival,rot,wall):
                    code='STAIR_ENTRY_UNSUPPORTED';break
                proposed.append((level['index'],room.get('id'),obj))
        if code:
            report['unsupported'].append({'core_id':core,'room_id':first.get('id'),'code':code})
        else:
            plans.extend(proposed)
    if not first_cores:
        report['unsupported'].append({'code':'STAIR_CORE_NOT_DECLARED'})
    # Materializing repeated templates must stay inside canonical room limits.
    affected={l['template'] for l,_ in levels if any(p[0]==l['index'] for p in plans)}
    preserve={l['template'] for l in model['levels'] if l.get('kind')=='roof'}
    extra=sum(max(0,sum(l['template']==template for l,_ in levels)-(0 if template in preserve else 1))*len(model['floors'][template]['rooms']) for template in affected)
    if sum(len(f['rooms']) for f in model['floors'].values())+extra>2048:
        plans=[];report['unsupported'].append({'code':'STAIR_INSTANCE_LIMIT_EXCEEDED'})
    if not plans:
        # No geometric authoring occurred: retain geometry references rather
        # than copying a possibly large warehouse merely to add a disclosure.
        out=dict(model);out['meta']={**(model.get('meta') or {}),'acs_stairs':copy.deepcopy(report)}
        return out,report,None
    out=copy.deepcopy(model)
    if plans:
        # Snapshot each source before altering shared instances. Keep its original
        # key for the first physical instance so explicit room selectors survive.
        # A roof can share an authored occupied template. Preserve that source
        # template and make physical occupied variants before adding any object.
        used={l['template']:True for l in out['levels'] if l.get('kind')=='roof'}
        sources=copy.deepcopy(out['floors'])
        affected={l['template'] for l,_ in levels if any(p[0]==l['index'] for p in plans)}
        for level,_ in levels:
            template=level['template']
            if template not in affected:
                continue
            if template in used:
                key=_id(template+'__stairs_'+str(level['index']))
                n=2
                while key in out['floors']:
                    key=_id(template+'__stairs_'+str(level['index'])+'_'+str(n));n+=1
                out['floors'][key]=copy.deepcopy(sources[template]);target_level=next(l for l in out['levels'] if l['index']==level['index'])
                target_level['template']=key;target_level['stair_source_template']=template
                target_level['stair_template_instance']={'schema':'acs.stair-template-instance/1',
                    'source_template':template,'template':key,'level_index':level['index'],
                    'room_mapping':[{'id':r.get('id'),'role':r.get('role')} for r in sources[template]['rooms']]}
            else:
                key=template;used[template]=True
            for index,rid,obj in plans:
                if index==level['index']:
                    room=next(r for r in out['floors'][key]['rooms'] if r['id']==rid)
                    room.setdefault('objects',[]).append(obj)
        report['generated_connections']=len(plans)
        stair_connections(out)
    meta=out.setdefault('meta',{})
    if not isinstance(meta,dict):
        return model,None,'STAIR_MODEL_INVALID'
    meta['acs_stairs']=copy.deepcopy(report)
    return out,report,None
