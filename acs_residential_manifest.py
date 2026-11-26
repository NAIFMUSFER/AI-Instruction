"""Compile explicit apartment quantities into the bounded planner's manifest.

Only confirmed, uniform per-apartment programs qualify. Geometry, openings and
all remaining written constraints still go through the normal proposal/review.
"""
import re
import acs_plan_chunks as PC

ROLES = ('bedroom', 'living', 'kitchen', 'bathroom', 'majlis')


def manifest(brief, requirements, plot=None):
    """``plot`` is a resolved acs_plot_rules block: the site becomes the land,
    the ground storey gets its own template (entrance lobby, or pilotis
    parking) and the upper storeys share a typical template without one."""
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
    # A confirmed building size is the envelope; the land is kept as context.
    land = None
    if plot is not None:
        # The land is the site; a confirmed building size is already the
        # envelope inside it (acs_plot_rules.resolve).
        width, depth = plot['land']['w'], plot['land']['d']
    elif get('building_width_m') is not None or get('building_depth_m') is not None:
        bw, bd = get('building_width_m'), get('building_depth_m')
        if any(type(v) not in (int, float) or not 0 < v <= 1000 for v in (bw, bd)):
            return None
        if any(type(v) in (int, float) and b > v + 1e-9 for b, v in ((bw, width), (bd, depth))):
            return None
        land = {'w': width, 'd': depth}
        width, depth = bw, bd
    pilotis = plot is not None and plot['parking']['placement'] == 'pilotis'
    if any(type(v) is not int or not 1 <= v <= 100 for v in (levels, units)) or units < levels - pilotis:
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
    extras = re.findall(r'بلكون|شرف[ةه]|غسيل|خادم|مكتب|مخزن|مستودع|مسبح|كراج|مواقف|غرف[ةه]?\s+(?:طعام|ملابس|عباد)|balcon|laundry|maid|office|storage|pool|garage|parking|dining|closet', normalized, re.I)
    # With plot rules, parking is planned from the plot block, not the prose.
    if any(not (plot is not None and word.lower() in {'مواقف', 'parking'}) for word in extras):
        return None
    if any(metric == 'room_count' and role not in ROLES for metric,role in by_key):
        return None
    # A negated/conditional elevator request needs interpretation, not a guess.
    negative = r'(?<!\w)(?:بدون|بلا|لا|ليس|اذا|ان|او|غير|اختياري|no|not|without|if|unless|optional)(?!\w)'
    core = r'(?:مصعد|\belevator\b|\blift\b)'
    if re.search(negative+r'.{0,20}'+core+'|'+core+r'.{0,20}'+negative, normalized, re.I):
        return None
    elevator = bool(re.search(r'مصعد|\belevator\b|\blift\b', normalized, re.I))
    homes = levels - 1 if pilotis else levels
    if homes < 1 or units < homes:
        return None
    distribution = [units//homes + (i < units % homes) for i in range(homes)]
    per_level = get('unit_count_per_level')
    if per_level is not None and any(n != per_level for n in distribution):
        return None
    # Explicit nonuniform distributions must not be silently overwritten.
    match = re.search(r'توزيع الشقق من الأرضي إلى الأعلى:\s*([^\n.]+)', brief)
    if match:
        numbers = [int(n) for n in re.findall(r'\d+', match.group(1))]
        if numbers != distribution:
            return None
    if plot is not None:
        return _plot_manifest(plot, counts, distribution, pilotis, levels, elevator)
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
                'acs_manifest_source':'confirmed_apartment_program',**({'acs_plot':land} if land else {})}}
    return {'kind':'outline','zones':zones,'envelope':envelope,'issues':[],
            'results':[],'pending':PC.group_by_template(zones),'rate':None,'index':0}


def _plot_manifest(plot, counts, distribution, pilotis, levels, elevator):
    """Ground and typical templates for a plot-rules generation.

    Ground: the building entrance lobby (external door on the street), the
    stairs and either the ground flats or, with pilotis, the parking hall.
    Typical upper floors: the stair landing (role lobby) and the flats, with
    no entrance lobby and no external door. Up to two flats open directly
    onto the lobby or landing; a common corridor is planned only for more
    flats per floor, and never when entries from the landing are requested."""
    landing = bool(plot.get('landing_entries'))
    zones, by_level = [], []
    def flats(template, count):
        for unit in range(1, count+1):
            unit_id = 'apartment_' + str(unit)
            for role, n in {**counts, 'corridor': 1}.items():
                for i in range(n):
                    zones.append({'id': template+'_'+unit_id+'_'+role+'_'+str(i+1),
                                  'role': role, 'template': template, 'unit_id': unit_id})
            # The flat's own foyer opens onto the lobby/landing beside the majlis.
            zones.append({'id': template+'_'+unit_id+'_entrance', 'role': 'entrance',
                          'template': template, 'unit_id': unit_id})
    def cores(template):
        if levels > 1:
            zones.append({'id': template+'_stairs', 'role': 'stairs', 'template': template, 'core_id': 'stairs_core'})
        if elevator:
            zones.append({'id': template+'_elevator', 'role': 'elevator', 'template': template, 'core_id': 'elevator_core'})
    upper = distribution if pilotis else distribution[1:]
    ground = 'parking_ground' if pilotis else 'residential_' + str(distribution[0]) + '_ground'
    zones.append({'id': ground+'_lobby', 'role': 'entrance', 'template': ground})
    if pilotis:
        zones.append({'id': ground+'_parking', 'role': 'parking', 'template': ground})
    else:
        flats(ground, distribution[0])
        if distribution[0] > 2 and not landing:
            zones.append({'id': ground+'_shared_corridor', 'role': 'corridor', 'template': ground})
    cores(ground)
    by_level.append(ground)
    for count in sorted(set(upper)):
        template = 'residential_' + str(count)
        flats(template, count)
        zones.append({'id': template+'_landing', 'role': 'lobby', 'template': template})
        if count > 2 and not landing:
            zones.append({'id': template+'_shared_corridor', 'role': 'corridor', 'template': template})
        cores(template)
    by_level += ['residential_' + str(n) for n in upper]
    if len(zones) > PC.MAX_BUILDING_ZONES:
        return None
    note = ('الدور الأرضي مواقف تحت المبنى ومدخل ودرج، والشقق في الأدوار فوقه.' if pilotis else
            'قالب للدور الأرضي ببهو المدخل، وقالب متكرر للأدوار العليا ببسطة الدرج دون باب خارجي.')
    envelope = {'site': {'w': plot['land']['w'], 'd': plot['land']['d']}, 'floor_height': 3.2, 'wall_h': 3.0, 'wall_t': 0.2,
        'levels': [{'index': i, 'template': t} for i, t in enumerate(by_level)],
        'meta': {'assumptions': ['ارتفاع الدور 3.2 م، وارتفاع الجدار 3 م وسماكته 0.2 م قيم أولية للمراجعة.',
                                 'توزيع متماثل للشقق ذات برنامج الغرف نفسه. ' + note],
                 'acs_manifest_source': 'confirmed_apartment_program'}}
    return {'kind': 'outline', 'zones': zones, 'envelope': envelope, 'issues': [],
            'results': [], 'pending': PC.group_by_template(zones), 'rate': None, 'index': 0}
