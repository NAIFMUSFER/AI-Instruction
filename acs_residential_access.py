"""Geometric access from declared apartment entrances, not code certification.

Apartment interiors connect through their own rooms to common circulation.
A single-family dwelling (villa or house) has no common corridor between
apartments: its rooms connect to its entrance, and on upper floors to its
stairs, through the dwelling's own rooms. Finished plans need aligned doors
through both sides of a wall. Street access, escape widths, accessibility and
regulatory compliance are outside this check.
"""
from collections import Counter, defaultdict
from contextlib import contextmanager
from contextvars import ContextVar
import math
import re

EPS = 0.0001
OPPOSITE = {'N':'S','S':'N','E':'W','W':'E'}
SINGLE_DWELLING = 'single_dwelling'
APARTMENTS = 'apartments'

# A reviewer that only receives the model (the plan review verifier) reads the
# revision's own brief and requirements from here. Unset, only the building's
# own shape is used, and anything unclear keeps the apartment rules.
_dwelling_brief = ContextVar('acs_residential_dwelling_brief', default=None)


@contextmanager
def dwelling_context(brief, requirements):
    token = _dwelling_brief.set((brief, requirements))
    try:
        yield
    finally:
        _dwelling_brief.reset(token)


# Whole words with optional Arabic conjunction/preposition/article prefixes and
# pronoun suffixes. Dual and plural houses (فيلتين، فلل، بيوت) are several
# dwellings and never count as one; dual apartments (شقتين) are apartments.
_OWNER = '(?:ي|ه|ها|نا|كم|هم)'
def _words(stems):
    return re.compile(r'(?<!\w)(?:و|ف)?(?:لل|ب|ل|ك)?(?:ال)?(?:' + '|'.join(stems)
                      + r')' + _OWNER + r'?(?!\w)', re.I)

def _feminine(stem, dual=False):
    return stem + '(?:[ةه]|ت' + ('(?:ين|ان)|ت' if dual else '') + _OWNER + ')'

_HOUSE = _words(['فيلا', _feminine('فيل'), _feminine('فل'), 'بيت', 'منزل', 'قصر',
                 'villa', 'house', 'townhouse'])
_APARTMENT = _words([_feminine('شق', True), 'شقق', _feminine('عمار', True), 'عمائر',
                     'apartments?', 'flats?', 'condo(?:minium)?s?'])
_UNITS = re.compile(r'وحدات\s+سكني[ةه]|residential\s+units', re.I)
# A roof stair or lift housing is not a house.
_CORE_HOUSING = re.compile(r'بيت\s+(?:ال)?(?:درج|سلم|مصعد)')
# The signed-in form appends «نوع المشروع: سكني / عمارة / فيلا» to every
# residential brief. That category label names both kinds, so its «عمارة» must
# not decide that a villa brief describes an apartment building.
_FORM_TYPE_LINE = re.compile(r'(?m)^\s*نوع المشروع\s*:.*$')


def _brief_says(text):
    text = _FORM_TYPE_LINE.sub(' ', text)
    text = _CORE_HOUSING.sub(' ', text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا'))
    if _APARTMENT.search(text) or _UNITS.search(text):
        return APARTMENTS
    return SINGLE_DWELLING if _HOUSE.search(text) else None


def _unit_ids(rooms):
    return {r['unit_id'] for r in rooms if isinstance(r, dict)
            and isinstance(r.get('unit_id'), str) and r['unit_id']}


def dwelling_kind(building, brief=None, requirements=None):
    """Return SINGLE_DWELLING for one villa/house, otherwise APARTMENTS.

    Apartment evidence always wins: two dwellings on one floor, a dwelling on a
    template repeated over several storeys, an apartment brief, or a confirmed
    unit count other than one. A single dwelling then needs positive evidence:
    a villa/house brief, exactly one confirmed unit, or one unit_id spanning
    every occupied room of the building.
    """
    if brief is None and requirements is None and _dwelling_brief.get() is not None:
        brief, requirements = _dwelling_brief.get()
    floors = building.get('floors') if isinstance(building, dict) else None
    levels = building.get('levels') if isinstance(building, dict) else None
    if not isinstance(floors, dict) or not isinstance(levels, list):
        return APARTMENTS
    occupied = Counter(l.get('template') for l in levels
                       if isinstance(l, dict) and l.get('kind') != 'roof')
    house_ids, rooms = set(), []
    for template, floor in floors.items():
        if template not in occupied or not isinstance(floor, dict) or not isinstance(floor.get('rooms'), list):
            continue
        ids = _unit_ids(floor['rooms'])
        if len(ids) > 1 or (ids and occupied[template] > 1):
            return APARTMENTS
        house_ids |= ids
        rooms += floor['rooms']
    said = _brief_says(brief) if isinstance(brief, str) else None
    if said == APARTMENTS:
        return APARTMENTS
    units = [r.get('expected') for r in requirements or [] if isinstance(r, dict) and r.get('metric') == 'unit_count']
    per_level = [r.get('expected') for r in requirements or [] if isinstance(r, dict) and r.get('metric') == 'unit_count_per_level']
    if (any(type(n) is not int or n != 1 for n in units)
            or (per_level and (not units or any(type(n) is not int or n != 1 for n in per_level)))):
        return APARTMENTS
    spans_house = (len(house_ids) == 1 and bool(rooms)
                   and all(isinstance(r, dict) and r.get('unit_id') in house_ids for r in rooms))
    return SINGLE_DWELLING if said == SINGLE_DWELLING or units or spans_house else APARTMENTS

def scoped(building):
    return any(r.get('unit_id') and r.get('role') == 'bedroom'
               for f in building.get('floors',{}).values() for r in f.get('rooms',[]))

def edge(room, side):
    x,z,w,d=room['rect']
    return (z if side=='N' else z+d,x,x+w) if side in {'N','S'} else (x if side=='W' else x+w,z,z+d)

def wall(room,side):
    value=room.get('walls')
    return False if value=='none' else side in value if isinstance(value,list) else True

def enclosed(room):
    """A space with no wall on any side (an open porch or canopy) is outdoors."""
    return any(wall(room,side) for side in OPPOSITE)

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

# A small ground-floor service room the brief opens to a yard (pump and filter
# room, garden store, pool bathroom) is reached from outside. Habitable rooms
# never are.
YARD_SERVICE_ROLES={'storage','equipment','utility','pump_room','service','bathroom'}
YARD_SERVICE_MAX_M2=6.0

def opens_outside(room,rooms):
    """A door on a side no enclosed room touches: it opens to the exterior."""
    return any(not any(abs(edge(room,side)[0]-edge(other,OPPOSITE[side])[0])<=EPS
                       and min(hi,edge(other,OPPOSITE[side])[2])-max(lo,edge(other,OPPOSITE[side])[1])>EPS
                       for other in rooms if other['id']!=room['id'] and enclosed(other))
               for side in OPPOSITE for lo,hi in portals(room,side))

def yard_service(room,rooms):
    role=str(room.get('role') or '').lower()
    rect=room.get('rect') or [0,0,0,0]
    small=len(rect)==4 and all(isinstance(v,(int,float)) for v in rect) and rect[2]*rect[3]<=YARD_SERVICE_MAX_M2
    return (role in YARD_SERVICE_ROLES or role=='other') and small and opens_outside(room,rooms)

def wall_less(room):
    """Declares no wall at all (walls "none" or []): a porch or canopy, never a room."""
    walls=room.get('walls')
    return (isinstance(walls,str) and walls.strip().lower()=='none') or (isinstance(walls,list) and not walls)

PORCH_ROLES={'porch','portico','canopy'}

def open_air(room,rooms):
    """A wall-less porch (a covered porch under an upper room) with a side on
    the exterior is outdoors: reached from the yard, it needs no door path."""
    if not wall_less(room) or str(room.get('role') or '').lower() not in PORCH_ROLES:return False
    for side in OPPOSITE:
        line,lo,hi=edge(room,side)
        cover=sorted((max(lo,edge(o,OPPOSITE[side])[1]),min(hi,edge(o,OPPOSITE[side])[2])) for o in rooms
                     if o is not room and not wall_less(o) and abs(edge(o,OPPOSITE[side])[0]-line)<=EPS)
        cursor=lo
        for a,b in cover:
            if a-cursor>EPS:return True
            cursor=max(cursor,b)
        if hi-cursor>EPS:return True
    return False

# Clear short side (m) below which a room does not work for its use, whatever
# the brief. Absolute floors, not planning targets (PLANNING_SYSTEM states
# those): IRC R304.3 (SBC 1101) habitable 2.13 m; Saudi 2024 domestic-worker
# room 2.1 m; IRC R311.6 hallway 0.914 m; NKBA work aisle 1.07 m + 0.6 m
# counter; IRC R307 water closet space 0.76 m. docs/research/residential_planning.md
MIN_SHORT_SIDE_M={'bedroom':2.1,'maid_room':2.1,'driver_room':2.1,'living':2.1,'majlis':2.1,'dining':2.1,
                  'office':2.1,'kitchen':1.6,'bathroom':0.9,'corridor':0.9,'entrance':0.9,'lobby':0.9}
ROLE_AR={'bedroom':'غرفة نوم','maid_room':'غرفة خادمة','driver_room':'غرفة سائق','living':'صالة','majlis':'مجلس',
         'dining':'غرفة طعام','office':'مكتب','kitchen':'مطبخ','bathroom':'حمام أو دورة مياه','corridor':'ممر',
         'entrance':'مدخل','lobby':'بهو'}

def narrow_rooms(building):
    """Advisory notes for rooms narrower than MIN_SHORT_SIDE_M for their role."""
    out=[]
    for template,floor in (building.get('floors') or {}).items():
        for room in (floor.get('rooms') or []) if isinstance(floor,dict) else []:
            if not isinstance(room,dict):continue
            role,rect=room.get('role'),room.get('rect')
            if role not in MIN_SHORT_SIDE_M or not isinstance(rect,list) or len(rect)!=4 \
                    or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in rect):continue
            short=min(rect[2],rect[3])
            if short<MIN_SHORT_SIDE_M[role]-EPS:
                name=room.get('name') if isinstance(room.get('name'),str) and room['name'].strip() else room.get('id')
                out.append({'code':'ROOM_TOO_NARROW','room_ref':[template,room.get('id')],'severity':'advisory',
                            'message':'['+template+'/'+str(room.get('id'))+'] «'+str(name).strip()[:60]+'» أقصر أضلاعه '
                            +('%g'%round(short,2))+' م، أقل من الحد الأدنى العملي '+('%g'%MIN_SHORT_SIDE_M[role])
                            +' م لـ'+ROLE_AR[role]+'؛ وسّعه.'})
    return out[:64]

def reachable(roots,allowed,graph):
    seen=set(roots)&allowed;pending=list(seen)
    while pending:
        for item in graph[pending.pop()]:
            if item in allowed and item not in seen:seen.add(item);pending.append(item)
    return seen

def issues(building,doors=True,dwelling=None):
    if not scoped(building):return []
    single=(dwelling or dwelling_kind(building))==SINGLE_DWELLING
    out=[]
    # A declared roof deck is unoccupied; this check proves apartment/common
    # circulation only, not roof access. Keep checking templates also used by
    # any occupied instance. Names and room IDs never grant this exemption.
    levels=building['levels']
    occupied_levels=[l for l in levels if l.get('kind')!='roof']
    occupied_templates={l['template'] for l in occupied_levels}
    roof_only_templates={l['template'] for l in levels if l.get('kind')=='roof'}-occupied_templates
    for template,floor in building['floors'].items():
        if template in roof_only_templates:continue
        rooms=floor['rooms'];by_id={r['id']:r for r in rooms};graph=defaultdict(set)
        def issue(rid,text):
            out.append({'code':'RESIDENTIAL_ACCESS_DISCONNECTED','room_ref':[template,rid],
                        'message':'['+template+'/'+rid+'] '+text,'severity':'error'})
        for i,a in enumerate(rooms):
            for b in rooms[i+1:]:
                if shared(a,b,doors):graph[a['id']].add(b['id']);graph[b['id']].add(a['id'])
        # One dwelling owns every room; apartments share only unit-less rooms.
        common=set(by_id) if single else {r['id'] for r in rooms if not r.get('unit_id')}
        ground=min((l['index'] for l in occupied_levels),default=0)
        at_ground=any(l['index']==ground and l['template']==template for l in occupied_levels)
        roots={r['id'] for r in rooms if r['id'] in common and r.get('role') in ({'entrance','lobby'} if at_ground else {'stairs','stair'})}
        if doors and at_ground:
            # A declared entrance needs an opening onto unoccupied exterior.
            # A wall-less space (open porch, canopy) is exterior: shared()
            # already treats a missing wall as fully open, and no compiler
            # builds a wall there, so a door into it opens to the outside.
            roots={rid for rid in roots if any(
                not any(abs(edge(by_id[rid],side)[0]-edge(other,OPPOSITE[side])[0])<=EPS
                        and min(hi,edge(other,OPPOSITE[side])[2])-max(lo,edge(other,OPPOSITE[side])[1])>EPS
                        for other in rooms if other['id']!=rid and enclosed(other))
                for side in OPPOSITE for lo,hi in portals(by_id[rid],side))}
        access=reachable(roots,common,graph)
        def outside(rid):
            # Reached from the yard: a porch open to it, or a small service
            # room (pool bathroom, pump room) whose door opens to it.
            return at_ground and (open_air(by_id[rid],rooms) or (doors and yard_service(by_id[rid],rooms)))
        if single:
            for rid in sorted(common-access):
                if outside(rid):continue
                issue(rid,('اربط هذا الفراغ بمدخل المسكن' if at_ground else 'اربط هذا الفراغ بدرج المسكن في هذا الدور')
                +' عبر فراغات المسكن وممراته، دون ممر مشترك بين شقق'+(' وبأبواب متقابلة متطابقة.' if doors else ' وبحواف متلامسة.'))
            continue
        for rid in sorted(common-access):
            if outside(rid):continue
            issue(rid,'اربط المدخل والممر المشترك والدرج والمصعد بمسار متصل'+(' وأبواب متقابلة متطابقة.' if doors else ' وحواف متلامسة.'))
        for unit in sorted({r.get('unit_id') for r in rooms if isinstance(r.get('unit_id'),str) and r['unit_id']}):
            own={r['id'] for r in rooms if r.get('unit_id')==unit}
            entries={rid for rid in own if by_id[rid].get('role') in {'corridor','entrance','living','majlis'} and graph[rid]&access}
            for rid in sorted(own-reachable(entries,own,graph)):
                if outside(rid):continue
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

def detail_issues(building,dwelling=None):
    import acs_validate as V
    findings,_=V.validate_building(building)
    return ([{'code':'ACS_GEOMETRY_FINDING','message':str(x)} for x in findings]
            + issues(building,dwelling=dwelling) + opening_collisions(building))[:128]
