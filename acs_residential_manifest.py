"""Compile explicit apartment quantities into the bounded planner's manifest.

Only confirmed, uniform per-apartment programs qualify. Geometry, openings and
all remaining written constraints still go through the normal proposal/review.
"""
import re
import acs_plan_chunks as PC

ROLES = ('bedroom', 'living', 'kitchen', 'bathroom', 'majlis')


def manifest(brief, requirements):
    by_key = {}
    for row in requirements:
        if row.get('confirmed') is not True or row.get('source') not in {'requested','inferred'}:
            return None
        key = (row.get('metric'), row.get('role'))
        if key in by_key:
            return None
        by_key[key] = row.get('expected')
    def get(metric, role=None):
        return by_key.get((metric, role))
    width, depth, levels, units = [get(k) for k in ('site_width_m','site_depth_m','level_count','unit_count')]
    if any(type(v) is not int or not 1 <= v <= 100 for v in (levels, units)) or units < levels:
        return None
    if any(type(v) not in (int,float) or not 0 < v <= 1000 for v in (width, depth)):
        return None
    counts = {role:get('room_count_per_unit',role) for role in ROLES}
    if any(type(n) is not int or not 0 <= n <= 8 for n in counts.values()):
        return None
    if any(counts[role] < 1 for role in ('bedroom','living','kitchen','bathroom')):
        return None
    if any(get('room_count',role) != n*units for role,n in counts.items()):
        return None
    # Do not replace explicit floor/core/room arrangements with an inferred one.
    # These less structured briefs retain the existing full outline stage.
    normalized = brief.replace('أ','ا').replace('إ','ا').replace('آ','ا')
    if re.search(r'ارتفاع|قبو|ميزانين|سطح|طابق تجاري|دور تجاري|height|basement|mezzanine', normalized, re.I):
        return None
    # Extra spaces mentioned only in prose still need the full outline. A
    # confirmed basic apartment card must not silently remove those requests.
    if re.search(r'بلكون|شرف[ةه]|غسيل|خادم|مكتب|مخزن|مستودع|مسبح|كراج|مواقف|غرف[ةه]?\s+(?:طعام|ملابس|عباد)|balcon|laundry|maid|office|storage|pool|garage|parking|dining|closet', normalized, re.I):
        return None
    if any(metric == 'room_count' and role not in ROLES for metric,role in by_key):
        return None
    # A negated/conditional elevator request needs interpretation, not a guess.
    negative = r'(?<!\w)(?:بدون|بلا|لا|ليس|اذا|ان|او|غير|اختياري|no|not|without|if|unless|optional)(?!\w)'
    core = r'(?:مصعد|\belevator\b|\blift\b)'
    if re.search(negative+r'.{0,20}'+core+'|'+core+r'.{0,20}'+negative, normalized, re.I):
        return None
    elevator = bool(re.search(r'مصعد|\belevator\b|\blift\b', normalized, re.I))
    distribution = [units//levels + (i < units % levels) for i in range(levels)]
    per_level = get('unit_count_per_level')
    if per_level is not None and any(n != per_level for n in distribution):
        return None
    # Explicit nonuniform distributions must not be silently overwritten.
    match = re.search(r'توزيع الشقق من الأرضي إلى الأعلى:\s*([^\n.]+)', brief)
    if match:
        numbers = [int(n) for n in re.findall(r'\d+', match.group(1))]
        if numbers != distribution:
            return None
    zones, templates = [], {}
    for count in sorted(set(distribution)):
        template = 'residential_' + str(count)
        templates[count] = template
        for unit in range(1,count+1):
            unit_id = 'apartment_' + str(unit)
            for role,n in {**counts,'corridor':1}.items():
                for i in range(n):
                    zones.append({'id':template+'_'+unit_id+'_'+role+'_'+str(i+1),
                                  'role':role,'template':template,'unit_id':unit_id})
        zones.append({'id':template+'_lobby','role':'entrance','template':template})
        if count > 1:
            zones.append({'id':template+'_shared_corridor','role':'corridor','template':template})
        if levels > 1:
            zones.append({'id':template+'_stairs','role':'stairs','template':template,'core_id':'stairs_core'})
        if elevator:
            zones.append({'id':template+'_elevator','role':'elevator','template':template,'core_id':'elevator_core'})
    if len(zones) > PC.MAX_BUILDING_ZONES:
        return None
    envelope = {'site':{'w':width,'d':depth},'floor_height':3.2,'wall_h':3.0,'wall_t':0.2,
        'levels':[{'index':i,'template':templates[n]} for i,n in enumerate(distribution)],
        'meta':{'assumptions':['ارتفاع الدور 3.2 م، وارتفاع الجدار 3 م وسماكته 0.2 م قيم أولية للمراجعة.',
                              'توزيع متماثل للشقق ذات برنامج الغرف نفسه، مع ممر داخلي لكل شقة ومدخل وممر مشتركين.'],
                'acs_manifest_source':'confirmed_apartment_program'}}
    return {'kind':'outline','zones':zones,'envelope':envelope,'issues':[],
            'results':[],'pending':PC.group_by_template(zones),'rate':None,'index':0}
