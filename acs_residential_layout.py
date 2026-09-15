"""Bounded, disclosed rectangular fallback for uniform two-apartment floors.

This is a concept subdivision, not a regulatory layout or a transcription of
an uploaded drawing. It is only used after a provider layout/detail fails.
Room proportions and circulation widths below are editable design assumptions.
"""
import copy
import re
from acs_plan_review import _geometry, _program
from acs_residential_manifest import manifest
from acs_residential_access import edge, OPPOSITE, EPS, detail_issues

NAMES={'bedroom':'غرفة نوم','living':'صالة','majlis':'مجلس','kitchen':'مطبخ',
       'bathroom':'دورة مياه','corridor':'ممر','entrance':'مدخل','stairs':'درج','elevator':'مصعد'}
WEIGHTS={'bedroom':1,'living':1.3,'majlis':1.1,'kitchen':1.7,'bathroom':.7,'entrance':.5}

def propose(brief, requirements):
    # Do not replace special dimensions, arrangements or extra requested spaces
    # with a generic subdivision. Those briefs retain the proposal/review path.
    if re.search(r'ارتداد|منور|فناء|حوش|ماستر|حمام داخلي|جناح|دوبلكس|مفتوح|شمالي[ةه]?|جنوبي[ةه]?|master|ensuite|en-suite|setback|courtyard|duplex',brief,re.I):
        return None
    if re.search(r'(?:غرف[ةه]|مجلس|مطبخ|صال[ةه]|حمام|درج|مصعد|ممر|مدخل)[^\n]{0,25}\d\s*[×x*]\s*\d',brief,re.I):
        return None
    allowed={'site_width_m','site_depth_m','level_count','unit_count','unit_count_per_level','room_count','room_count_per_unit'}
    if any(r.get('metric') not in allowed for r in requirements):return None
    cp=manifest(brief,requirements)
    if not cp or {l['template'] for l in cp['envelope']['levels']}!={'residential_2'}:return None
    b=copy.deepcopy(cp['envelope']);template='residential_2'
    W,D=b['site']['w'],b['site']['d']
    match=re.search(r'جهة الشارع:\s*(شمال|جنوب|شرق|غرب)',brief)
    front={'شمال':'N','جنوب':'S','شرق':'E','غرب':'W'}.get(match.group(1) if match else '', 'N')
    width,depth=(D,W) if front in {'E','W'} else (W,D)
    core_depth=4.;common_width=2.;private_width=1.4
    unit_width=(width-common_width)/2;unit_depth=depth-core_depth
    outer_width=(unit_width-private_width)*.58
    inner_width=unit_width-private_width-outer_width
    if outer_width<2.7 or inner_width<2 or unit_depth<8:return None
    rooms=[];connections=[]
    def add(zone,rect):
        r={k:v for k,v in zone.items() if k!='template'}
        r.update(name=NAMES[r['role']],rect=rect,walls=['N','S','E','W'],doors=[],windows=[],points=[])
        if r.get('unit_id'):
            ordinal=re.search(r'_(\d+)$',r['id'])
            r['name']+=(' '+ordinal.group(1) if ordinal else '')+' — الشقة '+r['unit_id'].rsplit('_',1)[-1]
        rooms.append(r);return r
    zones=cp['zones']
    common=add(next(z for z in zones if not z.get('unit_id') and z['role']=='corridor'),[unit_width,core_depth,common_width,unit_depth])
    has_stairs=any(z['role']=='stairs' for z in zones)
    has_lift=any(z['role']=='elevator' for z in zones)
    stair_width=4. if has_stairs else 0.
    lift_width=3. if has_lift else 0.
    lobby=add(next(z for z in zones if z['role']=='entrance'),[stair_width,0,width-stair_width-lift_width,core_depth])
    connections.append((lobby,common))
    for role,x,w in [('stairs',0,stair_width),('elevator',width-lift_width,lift_width)]:
        if w:
            r=add(next(z for z in zones if z['role']==role),[x,0,w,core_depth]);connections.append((lobby,r))
    for unit_number in (1,2):
        unit='apartment_'+str(unit_number);own=[z for z in zones if z.get('unit_id')==unit]
        # Work in the left unit's local coordinate frame, then mirror the right.
        local=[]
        def unit_add(z,rect):
            r=add(z,rect);local.append(r);return r
        corridor=unit_add(next(z for z in own if z['role']=='corridor'),[outer_width,core_depth,private_width,unit_depth])
        outer=[z for z in own if z['role'] in {'living','majlis','bedroom'}]
        outer.sort(key=lambda z:({'living':0,'majlis':1,'bedroom':2}[z['role']],z['id']))
        entrance={'id':template+'_'+unit+'_entrance','role':'entrance','unit_id':unit}
        inner=[entrance]+[z for z in own if z['role'] in {'kitchen','bathroom'}]
        for column,x,w in [(outer,0,outer_width),(inner,outer_width+private_width,inner_width)]:
            total=sum(WEIGHTS[z['role']] for z in column);cursor=core_depth
            for i,z in enumerate(column):
                end=depth if i==len(column)-1 else cursor+unit_depth*WEIGHTS[z['role']]/total
                d=end-cursor
                if min(w,d)<(2.7 if z['role'] in {'bedroom','living','majlis'} else 1.5):return None
                r=unit_add(z,[x,cursor,w,d]);connections.append((corridor,r))
                if z['role']=='entrance':connections.append((common,r))
                cursor=end
        if unit_number==2:
            for r in local:r['rect'][0]=width-r['rect'][0]-r['rect'][2]
    # Orient the entire common/private circulation system before adding portals.
    for r in rooms:
        x,z,w,d=r['rect']
        if front=='S':r['rect']=[x,D-z-d,w,d]
        elif front=='E':r['rect']=[W-z-d,x,d,w]
        elif front=='W':r['rect']=[z,D-x-w,d,w]
    def opening(r,kind,side,offset,w,h,sill=None):
        item={'id':r['id']+'_'+kind+'_'+str(len(r[kind])),'edge':side,
              'offset':offset,'width':w,'height':h}
        if kind=='doors':item['material']='wood'
        if sill is not None:item['sill']=sill
        r[kind].append(item)
    for a,c in connections:
        found=False
        for side,other in OPPOSITE.items():
            line,lo,hi=edge(a,side);line2,lo2,hi2=edge(c,other)
            low,high=max(lo,lo2),min(hi,hi2)
            if abs(line-line2)<EPS and high-low>=1.1:
                center=(low+high)/2
                opening(a,'doors',side,center-lo,.9,2.1)
                opening(c,'doors',other,center-lo2,.9,2.1)
                found=True;break
        if not found:return None
    _,lo,hi=edge(lobby,front)
    opening(lobby,'doors',front,(hi-lo)/2,1.2,2.1)
    unlit=[]
    for r in rooms:
        x,z,w,d=r['rect'];r['points']=[{'id':r['id']+'_light','type':'light','x':w/2,'z':d/2}]
        if r['role'] in {'corridor','entrance','stairs','elevator'}:continue
        for side,bound in [('N',0),('S',D),('W',0),('E',W)]:
            line,lo,hi=edge(r,side)
            if abs(line-bound)>EPS or hi-lo<1.8:continue
            if any(o['edge']==side for o in r['doors']):continue
            opening(r,'windows',side,(hi-lo)/2,.6 if r['role']=='bathroom' else 1.2,
                    .6 if r['role']=='bathroom' else 1.2,1.5 if r['role']=='bathroom' else .9)
            break
        if not r['windows']:unlit.append(r['name'])
    b['floors']={template:{'rooms':rooms}}
    b['meta']['assumptions'] += [
        'توزيع بديل محسوب بعد تعذر المقترح: شقتان حول ممر مشترك، مع مداخل خاصة وأبواب متقابلة؛ يحتاج مراجعة معمارية.',
        'عرض الممر المشترك 2 م والخاص 1.4 م، ونسب الغرف وأبعاد النواة والفتحات افتراضات تصميمية قابلة للتعديل وليست اشتراطات موثقة.',
        'لا يتضمن هذا التوزيع إثبات الارتدادات أو المواقف أو الإنشاء أو الإخلاء أو كفاية الإضاءة والتهوية.',
    ]
    if unlit:b['meta']['assumptions'].append('بعض المطابخ أو الحمامات داخلية بلا نافذة خارجية؛ يلزم حل تهوية ومراجعة الإضاءة قبل الاعتماد الهندسي.')
    if not match:b['meta']['assumptions'].append('وُضع المدخل شمالًا كافتراض لأن جهة الشارع غير محددة.')
    b['meta']['added']=['مدخل مستقل لكل شقة لتجنب المرور بغرفة نوم أو بشقة أخرى.']
    b['meta']['acs_layout_method']='bounded_rectangular_fallback_v1'
    from acs_residential_generation import check_rooms
    check_rooms(b)
    if _geometry(b)[0] or _program(b,brief,requirements) or detail_issues(b):return None
    return b
