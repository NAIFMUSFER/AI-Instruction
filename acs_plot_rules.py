"""Plot rules for residential concepts: buildable envelope, parking, basic layout checks.

ACS does not invent regulation. A plot rule is an input: the user states it,
or ACS applies a clearly labelled, editable default assumption that cites its
source. Every assumption is written in plain Arabic to ``meta.assumptions`` and
the resolved rules travel with the revision in ``meta.acs_plot_rules`` (a
server-derived block; the provider never authors it). Revisions without that
block keep their previous review unchanged.

Coordinates are the canonical plan's: x grows east, z grows south (north is
-Z), so the N edge of the land is z = 0 and the W edge is x = 0. With plot
rules the model's ``site`` is the land itself and every room sits inside the
buildable envelope (land minus setbacks, capped by the coverage ratio).

Defaults come from «اشتراطات إنشاء المباني السكنية» (Ministry of Municipalities
and Housing, July 2024). Values this file could not verify in that source are
marked ``unverified`` and are still disclosed as assumptions. Nothing here is
a compliance certificate: structure, fire code, MEP and municipal approval are
out of scope.
"""
from __future__ import annotations

import math
import re

SCHEMA = 'acs.plot-rules/1'
META_KEY = 'acs_plot_rules'
SIDES = ('N', 'E', 'S', 'W')
OPPOSITE = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}
SIDE_AR = {'N': 'الشمال', 'E': 'الشرق', 'S': 'الجنوب', 'W': 'الغرب'}
PLACEMENTS = ('front_setback', 'pilotis', 'none')
APARTMENTS, VILLA = 'apartments', 'villa'
EPS = 0.01  # metres: drawing tolerance, not a regulatory allowance

MOMAH_URL = ('https://momah.gov.sa/sites/default/files/2024-07/'
             'ashtratat%20a%27nsha%20almbany%20alsknyt%20almnshwrt%20%60ly%20mwq%60%20alwzart%20.pdf')
SOURCE = {'id': 'momah_residential_2024',
          'title': 'اشتراطات إنشاء المباني السكنية — وزارة البلديات والإسكان (يوليو 2024)',
          'url': MOMAH_URL, 'retrieved': '2026-11-26'}

# Defaults by dwelling type. ``ref`` is the clause in SOURCE; ``None`` = unverified.
DEFAULTS = {
    APARTMENTS: {
        'front_min_m': 3.0, 'front_ref': '§4-2-4 (4): خمس عرض الشارع ولا يقل عن 3 م',
        'street_min_m': 2.0, 'street_ref': '§4-2-4 (4): الشوارع الخلفية والجانبية خمس عرض الشارع ولا يقل عن 2 م',
        'neighbor_m': 2.0, 'neighbor_tall_m': 3.0,
        'neighbor_ref': '§4-2-4 (4): المجاورون 2 م حتى خمسة أدوار و3 م لما زاد',
        'coverage': 0.65, 'coverage_ref': '§4-2-4 (1): الدور الأرضي حتى 65٪ من مساحة الأرض',
        'parking_per_unit': 1.5, 'parking_ref': '§4-2-4 (6): 1.5 موقف لكل شقة داخل حدود الملكية',
    },
    VILLA: {
        'front_min_m': 3.0, 'front_wide_m': 6.0,
        'front_ref': '§4-1-4 (4، 5): خمس عرض الشارع ولا يقل عن 3 م، و6 م للشوارع 30 م فأكثر',
        'street_min_m': 2.0, 'street_ref': '§4-1-4 (4): الشوارع الخلفية والجانبية خمس عرض الشارع ولا يقل عن 2 م',
        'neighbor_m': 1.5, 'neighbor_tall_m': 1.5, 'neighbor_ref': '§4-1-4 (4): جهة المجاورين لا يقل عن 1.5 م',
        'coverage': 0.75, 'coverage_ref': '§4-1-4 (1): الدور الأرضي حتى 75٪ من مساحة الأرض',
        'parking_ref': '§4-1-4 (14): موقف لكل فيلا حتى 400 م² وموقفان لما زاد',
    },
}
PILOTIS_REF = '§4-4 (5): يسمح بأن يكون الدور الأرضي مواقف في العمائر متعددة الأدوار بارتفاع لا يقل عن 2.5 م'
FRONT_PARKING_REF = '§4-4 (8) و§4-1-4 (11): يسمح بإلغاء السور الأمامي لتكون مساحة الارتداد مواقف'
ASSUMED_STREET_WIDTH_M = 15.0   # unverified: used only when the street width is unknown
WIDE_STREET_M = 30.0
STALL_W, STALL_D = 2.5, 5.5     # unverified common stall size, perpendicular to the street
PATH_W = 1.5                    # assumption: pedestrian path to the entrance through the parking row
PILOTIS_M2_PER_STALL = 25.0     # unverified planning ratio including the aisle
CORE_M2 = 20.0                  # assumption: stairs and landing allowance per floor (preflight only)
PILOTIS_CORE_M2 = 30.0          # assumption: lobby and stairs on a pilotis ground floor
UNIT_AREA_TOLERANCE = 0.25      # assumption: the option estimate is coarse
ENTRY_MAJLIS_MAX_M = 5.0        # assumption: door-to-door distance for "next to the majlis"
ENTRY_BEDROOM_MIN_M = 3.0       # assumption: a bedroom door closer than this "faces" the entry
LANDING_MAX_M = 6.0             # assumption: a landing lobby, not a corridor
DEAD_END_MAX_M = 6.0            # unverified advisory threshold
MIN_ENVELOPE_M = 3.0
HABITABLE = {'bedroom', 'living', 'majlis', 'kitchen', 'dining', 'office', 'family'}
_ALLOWED = {'streets', 'street_width_m', 'setbacks_m', 'max_coverage', 'parking', 'landing_entries'}


class _Error(ValueError):
    pass


def _plan_error(code, message):
    from acs_plan_review import PlanError
    return PlanError(code, message)


def _num(value):
    return type(value) in (int, float) and math.isfinite(value)


def _fmt(value):
    value = round(float(value), 2)
    return str(int(value)) if value == int(value) else str(value)


# ── input ────────────────────────────────────────────────────────────────────
def validate_input(plot):
    """Strict, bounded copy of the client's plot block. Raises PlanError."""
    def bad(message='بيانات الأرض غير صالحة. راجع جهة الشارع والارتدادات والمواقف.'):
        return _plan_error('INVALID_PLOT_RULES', message)
    if not isinstance(plot, dict) or set(plot) - _ALLOWED:
        raise bad()
    streets = plot.get('streets', [])
    if (not isinstance(streets, list) or len(streets) > 2 or len(set(streets)) != len(streets)
            or any(s not in SIDES for s in streets)):
        raise bad('اختر شارعًا واحدًا أو شارعين على جهات مختلفة.')
    width = plot.get('street_width_m')
    if width is not None and (not _num(width) or not 4 <= width <= 120):
        raise bad('عرض الشارع يجب أن يكون بين 4 و120 م.')
    setbacks = plot.get('setbacks_m', {})
    if not isinstance(setbacks, dict) or set(setbacks) - set(SIDES):
        raise bad()
    for value in setbacks.values():
        if value is not None and (not _num(value) or not 0 <= value <= 30):
            raise bad('كل ارتداد يجب أن يكون بين 0 و30 م.')
    coverage = plot.get('max_coverage')
    if coverage is not None and (not _num(coverage) or not 0.2 <= coverage <= 1):
        raise bad('نسبة البناء يجب أن تكون بين 20٪ و100٪.')
    parking = plot.get('parking', {})
    if not isinstance(parking, dict) or set(parking) - {'placement', 'count'}:
        raise bad()
    placement = parking.get('placement', 'front_setback')
    count = parking.get('count')
    if placement not in PLACEMENTS or (count is not None and (type(count) is not int or not 0 <= count <= 500)):
        raise bad('اختر مكان المواقف وعددًا صحيحًا من 0 إلى 500.')
    landing = plot.get('landing_entries', False)
    if type(landing) is not bool:
        raise bad()
    return {'streets': list(streets), 'street_width_m': width,
            'setbacks_m': {s: setbacks.get(s) for s in SIDES},
            'max_coverage': coverage, 'parking': {'placement': placement, 'count': count},
            'landing_entries': landing}


def _confirmed(requirements, metric, role=None):
    values = {r.get('expected') for r in requirements or [] if isinstance(r, dict)
              and r.get('metric') == metric and (role is None or r.get('role') == role)
              and r.get('expected') is not None}
    return values.pop() if len(values) == 1 else None


def _normal(text):
    text = text.replace('أ', 'ا').replace('إ', 'ا').replace('آ', 'ا').replace('ة', 'ه')
    return re.sub('[ـً-ْ]', '', text)


_LANDING = re.compile(r'(?:مدخل|مداخل|باب|ابواب)\s+(?:كل\s+)?(?:ال)?(?:شقه|شقق)[^\n.]{0,30}?'
                      r'(?:بسطه|ردهه|صاله)\s+(?:ال)?(?:درج|سلم)')
_ZONING = (re.compile(r'(?:غرف\s+)?(?:ال)?نوم[^\n.]{0,25}?(?:بعيد|منفصل|معزول)[^\n.]{0,25}?(?:مدخل|ضيوف|مجلس)'),
           re.compile(r'خصوصيه\s+(?:ال)?ضيوف'),
           re.compile(r'(?:ال)?مجلس[^\n.]{0,20}?(?:عند|قرب|بجانب|جنب|قريب\s+من)\s+(?:ال)?مدخل'))


def landing_requested(brief):
    return bool(isinstance(brief, str) and _LANDING.search(_normal(brief)))


def zoning_requested(brief):
    text = _normal(brief) if isinstance(brief, str) else ''
    return any(p.search(text) for p in _ZONING)


def dwelling(brief, requirements):
    from acs_residential_access import SINGLE_DWELLING, _brief_says
    said = _brief_says(brief) if isinstance(brief, str) else None
    units = _confirmed(requirements, 'unit_count')
    if said == SINGLE_DWELLING and units in (None, 1):
        return VILLA
    if said is None and units == 1:
        return VILLA
    return APARTMENTS


def unit_area_estimate(option, requirements, brief):
    """The residential option card's per-flat estimate (residential-program.mjs).

    Same formula as ``residentialOptions``; a parity test keeps them in sync.
    Only for a confirmed per-flat card program (the brief names the option).
    """
    if option not in ('A', 'B', 'C') or not isinstance(brief, str) or 'الخيار المختار' not in brief:
        return None
    count = {role: _confirmed(requirements, 'room_count_per_unit', role)
             for role in ('bedroom', 'bathroom', 'majlis', 'living', 'kitchen')}
    if any(type(count[r]) is not int for r in ('bedroom', 'bathroom')):
        return None
    majlis = count['majlis'] if type(count['majlis']) is int else 0
    living = 24 if option == 'A' else 18
    estimate = (count['bedroom'] * 12 + living + 10 + count['bathroom'] * 4.5 + majlis * 18 + 10) * 1.15
    return int(math.floor(estimate + 0.5))  # Math.round for positive values


# ── resolution ───────────────────────────────────────────────────────────────
def resolve(plot, brief, requirements, option=None):
    """Deterministic plot rules (the stamped ``meta.acs_plot_rules``).

    Raises PlanError before any paid call when the land is unknown, the
    setbacks leave no envelope, or the requested program/parking cannot fit.
    """
    p = validate_input(plot)
    W, D = _confirmed(requirements, 'site_width_m'), _confirmed(requirements, 'site_depth_m')
    if not (_num(W) and _num(D) and W > 0 and D > 0):
        raise _plan_error('PLOT_SITE_REQUIRED', 'أدخل عرض الأرض وعمقها حتى تُحسب المساحة القابلة للبناء بعد الارتدادات.')
    W, D = float(W), float(D)
    kind = dwelling(brief, requirements)
    d = DEFAULTS[kind]
    levels = _confirmed(requirements, 'level_count')
    levels = levels if type(levels) is int and levels > 0 else 1
    units = _confirmed(requirements, 'unit_count')
    units = units if type(units) is int and units > 0 else (1 if kind == VILLA else None)
    assumptions = []

    def assume(text):
        assumptions.append('افتراض: ' + text)

    streets = list(p['streets'])
    street_source = 'user'
    if not streets:
        streets, street_source = ['N'], 'assumed'
        assume('الشارع من جهة الشمال لأن جهة الشارع غير محددة؛ حدّدها في بيانات الأرض لأنها تحدد المدخل والمواقف والارتدادات.')
    primary = streets[0]
    street_width = p['street_width_m']
    width_source = 'user'
    if street_width is None:
        street_width, width_source = ASSUMED_STREET_WIDTH_M, 'assumed'
        assume('عرض الشارع ' + _fmt(street_width) + ' م لأنه غير محدد (قيمة تقديرية غير متحقق منها)؛ الارتداد الأمامي يتبع عرض الشارع.')
    neighbor = d['neighbor_tall_m'] if levels > 5 else d['neighbor_m']
    setbacks, sources = {}, {}
    for side in SIDES:
        given = p['setbacks_m'][side]
        if given is not None:
            setbacks[side], sources[side] = float(given), 'user'
            continue
        if side == primary:
            value = (d['front_wide_m'] if kind == VILLA and street_width >= WIDE_STREET_M
                     else max(d['front_min_m'], street_width / 5))
            assume('ارتداد أمامي (' + SIDE_AR[side] + ') ' + _fmt(value) + ' م — ' + d['front_ref']
                   + '؛ عدّله حسب اشتراطات أمانة منطقتك.')
        elif side in streets:
            value = max(d['street_min_m'], ASSUMED_STREET_WIDTH_M / 5)
            assume('ارتداد على الشارع الثاني (' + SIDE_AR[side] + ') ' + _fmt(value) + ' م بافتراض عرضه '
                   + _fmt(ASSUMED_STREET_WIDTH_M) + ' م — ' + d['street_ref'] + '؛ عدّله حسب اشتراطات أمانة منطقتك.')
        else:
            value = neighbor
            assume('ارتداد جانبي (' + SIDE_AR[side] + ') ' + _fmt(value) + ' م — ' + d['neighbor_ref']
                   + '؛ عدّله حسب اشتراطات أمانة منطقتك.')
        setbacks[side], sources[side] = round(value, 2), 'default'
    coverage = p['max_coverage']
    coverage_source = 'user'
    if coverage is None:
        coverage, coverage_source = d['coverage'], 'default'
        assume('نسبة البناء القصوى ' + _fmt(coverage * 100) + '٪ — ' + d['coverage_ref']
               + '. طُبّقت على كل الأدوار احتياطًا؛ عدّلها حسب اشتراطات أمانة منطقتك.')

    placement = p['parking']['placement']
    if kind == VILLA:
        regulatory = 1 if W * D <= 400 + 1e-9 else 2
    else:
        regulatory = math.ceil(d['parking_per_unit'] * units - 1e-9) if units else None
    required = p['parking']['count'] if p['parking']['count'] is not None else regulatory
    required_source = 'user' if p['parking']['count'] is not None else 'default'
    if placement == 'none':
        assume('لن يُخصَّص موقف في هذا المقترح بناءً على اختيارك؛ الاشتراط الافتراضي '
               + (str(regulatory) + ' مواقف' if regulatory is not None else 'غير محسوب')
               + ' — ' + d['parking_ref'] + '. وفّرها في قبو أو حل آخر قبل الترخيص.')
        required = 0
    elif required is None:
        raise _plan_error('PLOT_PARKING_COUNT_REQUIRED', 'حدّد عدد الشقق أو عدد المواقف المطلوبة حتى تُحجز المواقف.')
    elif required_source == 'default':
        basis = ('1.5 موقف لكل شقة × ' + str(units) + ' شقق مقربة للأعلى' if kind == APARTMENTS
                 else 'لفيلا على أرض ' + _fmt(W * D) + ' م²')
        assume(str(required) + ' مواقف (' + basis + ') — ' + d['parking_ref'] + '.')
    elif regulatory is not None and required < regulatory:
        assumptions.append('تنبيه: عدد المواقف الذي أدخلته (' + str(required) + ') أقل من الافتراض النظامي ('
                           + str(regulatory) + ') — ' + d['parking_ref'] + '.')

    x0, x1, z0, z1 = setbacks['W'], W - setbacks['E'], setbacks['N'], D - setbacks['S']
    parking_depth = 0.0
    if placement == 'front_setback' and required > 0:
        parking_depth = STALL_D
        if setbacks[primary] < STALL_D:
            if primary == 'N': z0 = STALL_D
            elif primary == 'S': z1 = D - STALL_D
            elif primary == 'W': x0 = STALL_D
            else: x1 = W - STALL_D
        assume('المواقف في الارتداد الأمامي على شارع ' + SIDE_AR[primary] + ' بصف عمودي عمقه '
               + _fmt(STALL_D) + ' م (موقف ' + _fmt(STALL_W) + ' × ' + _fmt(STALL_D)
               + ' م مقاس شائع غير متحقق من المصدر) — ' + FRONT_PARKING_REF + '.')
    elif placement == 'pilotis':
        assume('المواقف تحت المبنى في الدور الأرضي (بيلوتي) والشقق في الأدوار فوقه — ' + PILOTIS_REF
               + '. السعة تقدير ' + _fmt(PILOTIS_M2_PER_STALL) + ' م² للموقف مع الممر (غير متحقق).')
    if x1 - x0 < MIN_ENVELOPE_M or z1 - z0 < MIN_ENVELOPE_M:
        raise _plan_error('PLOT_ENVELOPE_EMPTY', 'الارتدادات' + (' وصف المواقف' if parking_depth else '')
                          + ' لا تترك مساحة بناء كافية (أقل من 3 م) في أرض ' + _fmt(W) + ' × ' + _fmt(D)
                          + ' م. راجع الارتدادات أو مكان المواقف.')
    cap = coverage * W * D
    if (x1 - x0) * (z1 - z0) > cap + 1e-6:
        if primary in ('N', 'S'):
            depth = math.floor(cap / (x1 - x0) * 100) / 100
            if primary == 'N': z1 = z0 + depth
            else: z0 = z1 - depth
        else:
            depth = math.floor(cap / (z1 - z0) * 100) / 100
            if primary == 'W': x1 = x0 + depth
            else: x0 = x1 - depth
        assumptions.append('قُصّت المساحة القابلة للبناء من الخلف لتبقى ضمن نسبة البناء ' + _fmt(coverage * 100) + '٪.')
    envelope = [round(x0, 2), round(z0, 2), round(x1 - x0, 2), round(z1 - z0, 2)]
    footprint = None
    bw, bd = _confirmed(requirements, 'building_width_m'), _confirmed(requirements, 'building_depth_m')
    if _num(bw) and _num(bd):
        if bw > envelope[2] + EPS or bd > envelope[3] + EPS:
            raise _plan_error('PLOT_BUILDING_EXCEEDS_ENVELOPE', 'أبعاد المبنى المؤكدة ' + _fmt(bw) + ' × ' + _fmt(bd)
                              + ' م أكبر من المساحة القابلة للبناء بعد الارتدادات ' + _fmt(envelope[2]) + ' × '
                              + _fmt(envelope[3]) + ' م. صغّر المبنى أو راجع الارتدادات.')
        ex, ez, ew, ed = envelope
        fx = ex + (ew - bw) / 2 if primary in ('N', 'S') else (ex if primary == 'W' else ex + ew - bw)
        fz = ez + (ed - bd) / 2 if primary in ('E', 'W') else (ez if primary == 'N' else ez + ed - bd)
        footprint = envelope = [round(fx, 2), round(fz, 2), float(bw), float(bd)]
        assumptions.append('وُضع المبنى المؤكد ' + _fmt(bw) + ' × ' + _fmt(bd) + ' م داخل المساحة القابلة للبناء ملاصقًا لخط الارتداد على الشارع.')
    env_area = envelope[2] * envelope[3]

    frontage = W if primary in ('N', 'S') else D
    if placement == 'front_setback' and required > 0:
        capacity = max(0, int(math.floor((frontage - PATH_W) / STALL_W + 1e-9)) - 1)
        if capacity < required:
            raise _plan_error('PLOT_PARKING_DOES_NOT_FIT', 'المواقف المطلوبة ' + str(required)
                              + ' ولا يتسع الارتداد الأمامي بطول ' + _fmt(frontage) + ' م إلا لنحو ' + str(capacity)
                              + ' مواقف مع ممر المدخل. اختر المواقف تحت المبنى (بيلوتي)، أو قلّل عدد الشقق، أو اختر «بدون مواقف في هذا المقترح» إن كانت في قبو.')
    elif placement == 'pilotis':
        if levels < 2:
            raise _plan_error('PLOT_PILOTIS_NEEDS_LEVELS', 'المواقف تحت المبنى تحتاج دورين على الأقل: دور أرضي للمواقف وفوقه الشقق.')
        capacity = int(math.floor((env_area - PILOTIS_CORE_M2) / PILOTIS_M2_PER_STALL + 1e-9))
        if capacity < required:
            raise _plan_error('PLOT_PARKING_DOES_NOT_FIT', 'المواقف المطلوبة ' + str(required) + ' ولا يتسع الدور الأرضي ('
                              + _fmt(env_area) + ' م²) إلا لنحو ' + str(max(capacity, 0))
                              + ' مواقف. قلّل عدد الشقق أو راجع الارتدادات.')
    else:
        capacity = None

    residential_levels = levels - 1 if placement == 'pilotis' else levels
    per_level = _confirmed(requirements, 'unit_count_per_level')
    if placement == 'pilotis' and kind == APARTMENTS and units:
        if type(per_level) is int and per_level * residential_levels != units:
            raise _plan_error('PLOT_PILOTIS_PROGRAM_CONFLICT', 'اخترت المواقف تحت المبنى، فالدور الأرضي بلا شقق والشقق في '
                              + str(residential_levels) + ' أدوار فوقه. البرنامج المؤكد ' + str(units) + ' شقق بواقع '
                              + str(per_level) + ' في كل دور لا يتوافق مع ذلك. أكّد البدائل من جديد بعد اختيار مكان المواقف.')
    target = unit_area_estimate(option, requirements, brief) if kind == APARTMENTS else None
    if target is not None:
        assumptions.append('مساحة الشقة المستهدفة ≈ ' + str(target) + ' م² (±' + _fmt(UNIT_AREA_TOLERANCE * 100)
                           + '٪) من تقدير الخيار المختار؛ تقدير تخطيطي لا اشتراط.')
        if units and residential_levels > 0:
            per_floor = -(-units // residential_levels)
            need = per_floor * target * (1 - UNIT_AREA_TOLERANCE) + CORE_M2
            if env_area + 1e-6 < need:
                raise _plan_error('PLOT_ENVELOPE_TOO_SMALL', 'المساحة القابلة للبناء ' + _fmt(env_area) + ' م² في الدور لا تكفي '
                                  + str(per_floor) + ' شقق بنحو ' + str(target) + ' م² للشقة مع الدرج (تحتاج نحو '
                                  + _fmt(need) + ' م² على الأقل). قلّل الشقق في الدور أو عدد الغرف، أو راجع الارتدادات ونسبة البناء.')
    landing = p['landing_entries'] or landing_requested(brief)
    zoning = zoning_requested(brief)
    assumptions.append('المساحة القابلة للبناء: x من ' + _fmt(envelope[0]) + ' إلى ' + _fmt(envelope[0] + envelope[2])
                       + ' م وz من ' + _fmt(envelope[1]) + ' إلى ' + _fmt(envelope[1] + envelope[3]) + ' م ('
                       + _fmt(envelope[2]) + ' × ' + _fmt(envelope[3]) + ' م = ' + _fmt(env_area) + ' م²، '
                       + _fmt(env_area / (W * D) * 100) + '٪ من الأرض).')
    return {
        'schema': SCHEMA, 'dwelling': kind, 'land': {'w': W, 'd': D}, 'levels': levels,
        'units': units, 'streets': streets, 'street_source': street_source,
        'street_width_m': street_width, 'street_width_source': width_source,
        'setbacks_m': setbacks, 'setback_sources': sources, 'window_min_m': neighbor,
        'max_coverage': coverage, 'coverage_source': coverage_source,
        'envelope': envelope, 'building_footprint': footprint,
        'parking': {'placement': placement, 'required': required, 'required_source': required_source,
                    'regulatory_default': regulatory, 'depth_m': parking_depth,
                    'stall_m': [STALL_W, STALL_D], 'capacity_estimate': capacity},
        'landing_entries': landing, 'zoning_requested': zoning,
        'unit_area_target_m2': target, 'unit_area_tolerance': UNIT_AREA_TOLERANCE,
        'source': dict(SOURCE), 'assumptions': assumptions,
    }


def usable(rules):
    """Return a structurally valid stamped rules block, or None."""
    if not isinstance(rules, dict) or rules.get('schema') != SCHEMA:
        return None
    env, land = rules.get('envelope'), rules.get('land')
    if (not isinstance(env, list) or len(env) != 4 or not all(_num(v) for v in env)
            or not isinstance(land, dict) or not all(_num(land.get(k)) and land[k] > 0 for k in ('w', 'd'))
            or not isinstance(rules.get('streets'), list) or not rules['streets']
            or any(s not in SIDES for s in rules['streets'])
            or not isinstance(rules.get('setbacks_m'), dict)
            or not all(_num(rules['setbacks_m'].get(s)) for s in SIDES)
            or not isinstance(rules.get('parking'), dict)):
        return None
    return rules


def stamp(building, rules):
    """Write the server-derived rules and their Arabic assumptions (no provider input)."""
    meta = building.get('meta')
    if isinstance(meta, dict):
        meta.pop(META_KEY, None)
    if rules is None:
        return building
    if not isinstance(meta, dict):
        building['meta'] = meta = {}
    meta[META_KEY] = rules
    notes = meta.get('assumptions')
    if not isinstance(notes, list):
        meta['assumptions'] = notes = []
    for text in rules.get('assumptions', []):
        if text not in notes:
            notes.append(text)
    return building


def carry(before, candidate):
    """A chat edit keeps the revision's plot rules; the provider cannot change them."""
    rules = (before.get('meta') or {}).get(META_KEY) if isinstance(before, dict) else None
    meta = candidate.get('meta')
    if isinstance(meta, dict):
        meta.pop(META_KEY, None)
    if rules is not None:
        candidate.setdefault('meta', {})
        if isinstance(candidate['meta'], dict):
            candidate['meta'][META_KEY] = rules
    return candidate


# ── prompts ──────────────────────────────────────────────────────────────────
def prompt_text(rules, ground_template=None, typical_template=None):
    """Arabic plot section of the planning prompt; numbers only from the rules."""
    W, D = rules['land']['w'], rules['land']['d']
    x, z, w, d = rules['envelope']
    sb = rules['setbacks_m']
    park = rules['parking']
    lines = ['اشتراطات الأرض (مدخلات المستخدم أو افتراضات معلنة قابلة للتعديل، وليست شهادة مطابقة):',
             '- الأرض ' + _fmt(W) + ' × ' + _fmt(D) + ' م: اجعل site.w = ' + _fmt(W) + ' وsite.d = ' + _fmt(D)
             + '. الشمال حافة z=0 والجنوب z=' + _fmt(D) + ' والغرب x=0 والشرق x=' + _fmt(W) + '.',
             '- الشارع: ' + ' و'.join(SIDE_AR[s] for s in rules['streets']) + '. الارتدادات: '
             + '، '.join(SIDE_AR[s] + ' ' + _fmt(sb[s]) + ' م' for s in SIDES) + '.',
             '- المساحة القابلة للبناء: x من ' + _fmt(x) + ' إلى ' + _fmt(x + w) + ' وz من ' + _fmt(z) + ' إلى '
             + _fmt(z + d) + ' (' + _fmt(w) + ' × ' + _fmt(d) + ' م). ضع كل غرف كل الأدوار داخلها، ولا تضع أي غرفة في الارتدادات. '
             'إن زادت عن حاجة البرنامج فلا تكبّر الشقق لملئها؛ اترك الباقي فراغًا خارجيًا.']
    if park['placement'] == 'front_setback' and park['required']:
        lines.append('- المواقف: ' + str(park['required']) + ' مواقف في الارتداد الأمامي على شارع '
                     + SIDE_AR[rules['streets'][0]] + ' تحسبها المنصة؛ لا ترسمها غرفًا واترك واجهة المدخل مطلة عليها.')
    elif park['placement'] == 'pilotis':
        lines.append('- المواقف: الدور الأرضي مواقف تحت المبنى (بيلوتي) بفراغ role=parking وجدران walls="none"، '
                     'ومعه مدخل العمارة والدرج فقط، بلا شقق. الشقق في الأدوار فوقه. ' + str(park['required']) + ' مواقف مطلوبة.')
    lines.append('- مدخل ' + ('المسكن' if rules['dwelling'] == VILLA else 'العمارة') + ' في الدور الأرضي فقط، '
                 'وبابه الخارجي على واجهة تطل على الشارع.')
    if rules['dwelling'] == APARTMENTS:
        lines.append('- قالب الدور الأرضي' + (' (' + ground_template + ')' if ground_template else '')
                     + ' مستقل عن قالب الدور المتكرر' + (' (' + typical_template + ')' if typical_template else '')
                     + '. الدور المتكرر بلا باب خارجي وبلا بهو مدخل؛ فراغه المشترك بسطة/ردهة الدرج (role=lobby) '
                     'ملاصقة للدرج.')
        if rules['landing_entries']:
            lines.append('- مدخل كل شقة في الأدوار المتكررة يفتح مباشرة على بسطة الدرج (ردهة لا يزيد طولها عن '
                         + _fmt(LANDING_MAX_M) + ' م)، لا على ممر طويل، ولا تترك ممرًا مشتركًا مسدود النهاية.')
    if rules.get('unit_area_target_m2'):
        lines.append('- مساحة كل شقة (مجموع مستطيلات غرفها) ≈ ' + str(rules['unit_area_target_m2']) + ' م² (±'
                     + _fmt(rules['unit_area_tolerance'] * 100) + '٪).')
    lines.append('- النوافذ: لا نافذة ولا باب على جدار يقع على حد أرض جار (مسافة 0). نوافذ الغرف السكنية على واجهة '
                 'تطل على الشارع أو تبعد عن حد الجار ' + _fmt(rules['window_min_m']) + ' م على الأقل.')
    lines.append('- الخصوصية: اجعل باب الشقة أو المسكن بجوار المجلس (منطقة الضيوف)، ولا يواجه باب غرفة نوم باب المدخل '
                 'على أقل من ' + _fmt(ENTRY_BEDROOM_MIN_M) + ' م.')
    return '\n'.join(lines)


def opening_context(rules, building):
    levels = _occupied(building)
    ground = levels[0]['template'] if levels else None
    return {'land': rules['land'], 'streets': rules['streets'], 'envelope': rules['envelope'],
            'setbacks_m': rules['setbacks_m'], 'window_min_m': rules['window_min_m'],
            'ground_template': ground,
            'upper_templates': sorted({l['template'] for l in levels[1:]} - {ground})}


PLANNING_ADDENDUM = '''\nPLOT RULES are supplied in the brief. They are user inputs or labelled
default assumptions: use exactly those numbers and no other setback, coverage or
parking value. site is the whole land; put every room of every storey inside the
stated buildable envelope rectangle and leave the setbacks empty. The ground
storey uses its own template with the building entrance lobby and its external
door on a street side. Upper storeys use a typical template with no external
door and no entrance lobby: their common space is the stair landing (role
lobby) beside the stairs. With up to two apartments per storey the lobby or
landing is the common circulation and each apartment's own entrance opens onto
it next to its majlis; add a common corridor only for more apartments, and
never when entries from the landing are requested.'''

OPENINGS_ADDENDUM = '''\ncontext.plot holds the PLOT RULES. External doors exist only on the ground
template: the building or dwelling entrance door faces a street side in
plot.streets. Never put an external door on an upper template (it would open
onto the void). Never put a window or door on a wall lying on a plot line of a
non-street side (distance 0). Windows of bedrooms, living rooms, majlis and
kitchens go on façades facing a street or at least plot.window_min_m from a
non-street plot line. Keep each apartment or dwelling entrance door next to the
majlis, and no bedroom door within 3 m of the entrance door. The lobby or
landing counts as the COMMON corridor when the plan has no separate one.'''


def repair_instruction(findings):
    env = next((f.get('envelope') for f in findings if f.get('code') == 'PLOT_OUTSIDE_ENVELOPE'), None)
    if not (isinstance(env, list) and len(env) == 4 and all(_num(v) for v in env)):
        return ''
    x, z, w, d = env
    return ('\nBUILDABLE ENVELOPE: every room rect must satisfy x >= ' + _fmt(x) + ', z >= ' + _fmt(z)
            + ', x + w <= ' + _fmt(x + w) + ', z + d <= ' + _fmt(z + d) + '. Move or resize the rooms listed in '
            'PLOT_OUTSIDE_ENVELOPE findings (keep cores aligned between storeys); do not change site.')


# ── geometry helpers ─────────────────────────────────────────────────────────
def _occupied(building):
    levels = [l for l in (building.get('levels') or []) if isinstance(l, dict) and l.get('kind') != 'roof'
              and isinstance(l.get('template'), str) and l['template'] in (building.get('floors') or {})]
    return sorted(levels, key=lambda l: l['index'] if type(l.get('index')) is int else 0)


def _rooms(building, template):
    floor = (building.get('floors') or {}).get(template)
    rooms = floor.get('rooms') if isinstance(floor, dict) else None
    return [r for r in rooms or [] if isinstance(r, dict) and isinstance(r.get('rect'), list)
            and len(r['rect']) == 4 and all(_num(v) for v in r['rect'])]


def _inside(rect, env):
    x, z, w, d = rect
    ex, ez, ew, ed = env
    return x >= ex - EPS and z >= ez - EPS and x + w <= ex + ew + EPS and z + d <= ez + ed + EPS


def _door_width(o):
    value = o.get('width', o.get('w'))
    return value if _num(value) and value > 0 else 0.9


def _center(room, opening):
    x, z, w, d = room['rect']
    off = opening.get('offset')
    if not _num(off):
        return None
    edge = opening.get('edge')
    if edge == 'N': return (x + off, z)
    if edge == 'S': return (x + off, z + d)
    if edge == 'W': return (x, z + off)
    if edge == 'E': return (x + w, z + off)
    return None


_OUT = {'N': (0, -1), 'S': (0, 1), 'W': (-1, 0), 'E': (1, 0)}


def _at(rooms, point, skip=None):
    px, pz = point
    for r in rooms:
        if r is skip:
            continue
        x, z, w, d = r['rect']
        if x - 1e-6 <= px <= x + w + 1e-6 and z - 1e-6 <= pz <= z + d + 1e-6:
            return r
    return None


def _across(rooms, room, opening, step=0.05):
    c = _center(room, opening)
    if c is None:
        return None, None
    dx, dz = _OUT[opening['edge']]
    return _at(rooms, (c[0] + dx * step, c[1] + dz * step), skip=room), c


def _plot_distance(rules, room, side):
    W, D = rules['land']['w'], rules['land']['d']
    x, z, w, d = room['rect']
    return {'N': z, 'S': D - (z + d), 'W': x, 'E': W - (x + w)}[side]


def _label(template, room):
    return '[' + template + '/' + str(room.get('id')) + '] '


def _entries(rooms, single):
    """Entry doors as (unit, room, centre, room across). Apartments open onto a
    common room; a single dwelling's entry is a ground-floor external door."""
    out = []
    for room in rooms:
        unit = room.get('unit_id')
        if not single and not (isinstance(unit, str) and unit):
            continue
        for door in room.get('doors') or []:
            if not isinstance(door, dict) or door.get('edge') not in _OUT:
                continue
            other, c = _across(rooms, room, door)
            if c is None:
                continue
            if single:
                if other is None:
                    out.append((unit or 'dwelling', room, c, None))
            elif other is not None and not other.get('unit_id'):
                out.append((unit, room, c, other))
    return out


def _door_centres(room):
    return [c for c in (_center(room, o) for o in room.get('doors') or [] if isinstance(o, dict)) if c]


def _signature(rooms):
    def openings(room, kind):
        return [(o.get('edge'), o.get('offset'), o.get('width', o.get('w'))) for o in room.get(kind) or []
                if isinstance(o, dict)]
    return repr([(r.get('id'), r.get('role'), r.get('unit_id'), r['rect'], openings(r, 'doors'),
                  openings(r, 'windows')) for r in rooms])


def _groups(building, part='all'):
    """Occupied storeys grouped by identical room layout: [(template, [indices])].

    Stair variants copy their source floor, so identical storeys are reported
    once. ``part`` is 'all', 'ground' (lowest occupied storey) or 'upper'."""
    levels = _occupied(building)
    if not levels:
        return []
    ground = levels[0]['index']
    groups = {}
    for level in levels:
        is_ground = level['index'] == ground
        if (part == 'ground' and not is_ground) or (part == 'upper' and is_ground):
            continue
        key = (is_ground, _signature(_rooms(building, level['template'])))
        groups.setdefault(key, (level['template'], []))[1].append(level['index'])
    return list(groups.values())


def _where(indices):
    names = ['الأرضي' if i == 0 else str(i) for i in indices]
    return ' (الدور ' + names[0] + ')' if len(names) == 1 else ' (الأدوار ' + '، '.join(names) + ')'


# ── checks ───────────────────────────────────────────────────────────────────
def envelope_findings(building, rules):
    """Per-room envelope findings for the layout repair (structured)."""
    out = []
    env = rules['envelope']
    for template in dict.fromkeys(l['template'] for l in _occupied(building)):
        for room in _rooms(building, template):
            if not _inside(room['rect'], env):
                out.append({'code': 'PLOT_OUTSIDE_ENVELOPE', 'room_ref': [template, room.get('id')],
                            'rect': room['rect'], 'envelope': env})
    return out[:128]


def fit_to_envelope(building, rules):
    """Translate every occupied storey by one shared offset when the layout's
    bounding box fits the envelope but sits outside it. Sizes, cores and
    openings are unchanged; anything else is left to the repair step."""
    levels = _occupied(building)
    templates = list(dict.fromkeys(l['template'] for l in levels))
    rects = [r['rect'] for t in templates for r in _rooms(building, t)]
    if not rects:
        return building, False
    bx0 = min(r[0] for r in rects); bz0 = min(r[1] for r in rects)
    bx1 = max(r[0] + r[2] for r in rects); bz1 = max(r[1] + r[3] for r in rects)
    ex, ez, ew, ed = rules['envelope']
    if bx1 - bx0 > ew + EPS or bz1 - bz0 > ed + EPS or all(_inside(r, rules['envelope']) for r in rects):
        return building, False
    dx = ex - bx0 if bx0 < ex else (ex + ew - bx1 if bx1 > ex + ew else 0.0)
    dz = ez - bz0 if bz0 < ez else (ez + ed - bz1 if bz1 > ez + ed else 0.0)
    import copy
    moved = copy.deepcopy(building)
    for template in templates:
        for room in _rooms(moved, template):
            room['rect'] = [round(room['rect'][0] + dx, 4), round(room['rect'][1] + dz, 4)] + room['rect'][2:]
    meta = moved.setdefault('meta', {})
    if isinstance(meta, dict) and isinstance(meta.setdefault('assumptions', []), list):
        meta['assumptions'].append('نُقلت غرف كل الأدوار إزاحةً واحدة (' + _fmt(dx) + '، ' + _fmt(dz)
                                   + ' م) لتقع داخل المساحة القابلة للبناء دون تغيير أبعادها؛ تعديل حتمي يحتاج مراجعة معمارية.')
    return moved, True


def opening_findings(building, rules):
    """Blocking opening findings: openings on plot lines and upper external doors."""
    blocking, advisory = [], []
    _openings(building, rules, blocking, advisory)
    _upper_doors(building, blocking, advisory)
    return blocking


def _openings(building, rules, blocking, advisory):
    """Façade openings against the plot lines, one finding per storey group and side."""
    streets = set(rules['streets'])
    minimum = rules['window_min_m']
    for template, indices in _groups(building):
        rooms = _rooms(building, template)
        found = {}
        for room in rooms:
            for kind in ('windows', 'doors'):
                for o in room.get(kind) or []:
                    side = o.get('edge') if isinstance(o, dict) else None
                    if side not in _OUT or side in streets:
                        continue
                    other, c = _across(rooms, room, o)
                    if c is None or other is not None:
                        continue  # interior wall: not a façade opening
                    gap = _plot_distance(rules, room, side)
                    limit = min(rules['setbacks_m'][side], minimum)
                    if gap < EPS:
                        code = 'PLOT_OPENING_ON_BOUNDARY'
                    elif kind == 'windows' and room.get('role') in HABITABLE and gap < limit - EPS:
                        code = 'PLOT_WINDOW_TOO_CLOSE'
                    elif kind == 'windows' and room.get('role') in HABITABLE and gap < minimum - EPS:
                        code = 'PLOT_WINDOW_BELOW_DEFAULT'
                    else:
                        continue
                    rows = found.setdefault((code, side), [])
                    if room not in rows:
                        rows.append(room)
                    found[(code, side, 'gap')] = min(found.get((code, side, 'gap'), 1e9), gap)
        for key, rows in found.items():
            if len(key) != 2:
                continue
            code, side = key
            gap = found[(code, side, 'gap')]
            names = '، '.join(str(r.get('name') or r.get('id')) for r in rows[:6]) + ('…' if len(rows) > 6 else '')
            head = _label(template, rows[0])
            if code == 'PLOT_OPENING_ON_BOUNDARY':
                text = ('فتحات على حد أرض الجار من جهة ' + SIDE_AR[side] + ' (مسافة 0 م) في: ' + names
                        + '. انقلها إلى واجهة تطل على الشارع أو على ارتداد.')
            elif code == 'PLOT_WINDOW_TOO_CLOSE':
                text = ('نوافذ غرف سكنية تبعد ' + _fmt(gap) + ' م فقط عن حد الجار من جهة ' + SIDE_AR[side]
                        + ' (الحد الأدنى ' + _fmt(min(rules['setbacks_m'][side], minimum)) + ' م) في: ' + names + '.')
            else:
                text = ('نوافذ على ارتداد ' + _fmt(gap) + ' م من جهة ' + SIDE_AR[side] + '، أقل من الافتراض النظامي '
                        + _fmt(minimum) + ' م للارتداد الجانبي، في: ' + names + '. تأكد من اشتراطات أمانتك.')
            item = {'code': code, 'room_ref': [template, rows[0].get('id')], 'message': head + text + _where(indices)}
            (advisory if code == 'PLOT_WINDOW_BELOW_DEFAULT' else blocking).append(
                dict(item, severity='advisory' if code == 'PLOT_WINDOW_BELOW_DEFAULT' else 'error'))


def _upper_doors(building, blocking, advisory):
    levels = _occupied(building)
    if len(levels) < 2:
        return
    for template, indices in _groups(building, 'upper'):
        rooms = _rooms(building, template)
        below = [r['rect'] for l in levels if l['index'] < min(indices) for r in _rooms(building, l['template'])]
        where = _where(indices)
        for room in rooms:
            if room.get('role') == 'entrance' and not room.get('unit_id'):
                advisory.append({'code': 'PLOT_UPPER_ENTRANCE_LOBBY', 'room_ref': [template, room.get('id')],
                                 'severity': 'advisory', 'message': _label(template, room)
                                 + 'بهو مدخل العمارة يتكرر في دور علوي؛ فراغ الدور المتكرر المشترك بسطة الدرج فقط.' + where})
            for door in room.get('doors') or []:
                if not isinstance(door, dict) or door.get('edge') not in _OUT:
                    continue
                other, c = _across(rooms, room, door)
                if c is None or other is not None:
                    continue
                dx, dz = _OUT[door['edge']]
                point = (c[0] + dx * 0.5, c[1] + dz * 0.5)
                over = any(x - 1e-6 <= point[0] <= x + w + 1e-6 and z - 1e-6 <= point[1] <= z + d + 1e-6
                           for x, z, w, d in below)
                item = {'room_ref': [template, room.get('id')]}
                if over:
                    advisory.append(dict(item, code='PLOT_UPPER_TERRACE_DOOR', severity='advisory',
                                         message=_label(template, room) + 'باب خارجي في دور علوي يفتح على سطح الدور الأسفل؛ '
                                         'يحتاج سطحًا مستخدمًا وحاجزًا وتصريف مياه قبل اعتماده.' + where))
                else:
                    blocking.append(dict(item, code='PLOT_UPPER_EXTERIOR_DOOR', severity='error',
                                         message=_label(template, room) + 'باب خارجي في دور علوي يفتح على الفراغ (لا يوجد تحته بناء). '
                                         'الأبواب الخارجية ومدخل العمارة في الدور الأرضي فقط.' + where))


def stalls(building, rules):
    """Front-setback stall rectangles derived from the ground floor (not stored)."""
    park = rules['parking']
    if park.get('placement') != 'front_setback' or not park.get('required'):
        return []
    levels = _occupied(building)
    if not levels:
        return []
    W, D = rules['land']['w'], rules['land']['d']
    primary = rules['streets'][0]
    rooms = _rooms(building, levels[0]['template'])
    depth = min([_plot_distance(rules, r, primary) for r in rooms] or [0.0])
    if depth < STALL_D - EPS:
        return []
    along = W if primary in ('N', 'S') else D
    gap = along / 2
    for room in rooms:
        for door in room.get('doors') or []:
            if isinstance(door, dict) and door.get('edge') == primary:
                other, c = _across(rooms, room, door)
                if c is not None and other is None:
                    gap = c[0] if primary in ('N', 'S') else c[1]
                    if room.get('role') in ('entrance', 'lobby') and not room.get('unit_id'):
                        break
        else:
            continue
        break
    out = []
    for lo, hi in ((0.0, gap - PATH_W / 2), (gap + PATH_W / 2, along)):
        n = int(math.floor((hi - lo) / STALL_W + 1e-9)) if hi > lo else 0
        for i in range(n):
            s = round(lo + i * STALL_W, 3)
            out.append({'N': [s, 0.0, STALL_W, STALL_D], 'S': [s, D - STALL_D, STALL_W, STALL_D],
                        'W': [0.0, s, STALL_D, STALL_W], 'E': [W - STALL_D, s, STALL_D, STALL_W]}[primary])
    return out


def parking_capacity(building, rules):
    park = rules['parking']
    if park.get('placement') == 'front_setback':
        return len(stalls(building, rules))
    if park.get('placement') == 'pilotis':
        levels = _occupied(building)
        area = sum(r['rect'][2] * r['rect'][3] for r in _rooms(building, levels[0]['template'])
                   if r.get('role') == 'parking') if levels else 0
        return int(math.floor(area / PILOTIS_M2_PER_STALL + 1e-9))
    return 0


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _zoning(building, rules, blocking, advisory):
    hard = bool(rules.get('zoning_requested'))
    target = blocking if hard else advisory
    severity = 'error' if hard else 'advisory'
    single = rules.get('dwelling') == VILLA
    for template, indices in _groups(building, 'ground' if single else 'all'):
        where = _where(indices)
        rooms = _rooms(building, template)
        entries = _entries(rooms, single)
        for unit in dict.fromkeys(e[0] for e in entries):
            doors = [(room, c) for u, room, c, _ in entries if u == unit]
            own = rooms if single else [r for r in rooms if r.get('unit_id') == unit]
            majlis = [r for r in own if r.get('role') == 'majlis']
            if majlis:
                own_entry = any(room.get('role') == 'majlis' for room, _ in doors)
                near = min(_distance(c, m) for _, c in doors for r in majlis for m in _door_centres(r) or [(1e9, 1e9)])
                if not own_entry and near > ENTRY_MAJLIS_MAX_M + EPS:
                    target.append({'code': 'PLOT_ZONING_MAJLIS_FAR', 'room_ref': [template, majlis[0].get('id')],
                                   'severity': severity, 'message': _label(template, majlis[0]) + 'المجلس يبعد نحو '
                                   + _fmt(near) + ' م عن باب ' + ('المسكن' if single else 'الشقة') + '؛ اجعله بجوار المدخل (حتى '
                                   + _fmt(ENTRY_MAJLIS_MAX_M) + ' م) حتى لا يعبر الضيوف منطقة الأسرة.' + where})
            for bed in (r for r in own if r.get('role') == 'bedroom'):
                close = min([_distance(c, b) for _, c in doors for b in _door_centres(bed)] or [1e9])
                if close < ENTRY_BEDROOM_MIN_M - EPS:
                    target.append({'code': 'PLOT_ZONING_BEDROOM_AT_ENTRY', 'room_ref': [template, bed.get('id')],
                                   'severity': severity, 'message': _label(template, bed) + 'باب غرفة النوم على بعد '
                                   + _fmt(close) + ' م من باب ' + ('المسكن' if single else 'الشقة') + '؛ أبعده '
                                   + _fmt(ENTRY_BEDROOM_MIN_M) + ' م على الأقل أو اجعل منطقة الضيوف بينهما.' + where})


def _landing(building, rules, blocking, advisory):
    if not rules.get('landing_entries') or rules.get('dwelling') == VILLA:
        return
    for template, indices in _groups(building, 'upper'):
        rooms = _rooms(building, template)
        stairs = [r for r in rooms if r.get('role') in ('stairs', 'stair')]
        landings = set()
        for room in rooms:
            if room.get('unit_id') or room.get('role') in ('stairs', 'stair', 'elevator'):
                continue
            if max(room['rect'][2], room['rect'][3]) > LANDING_MAX_M + EPS:
                continue
            for door in room.get('doors') or []:
                if isinstance(door, dict) and door.get('edge') in _OUT:
                    other, _ = _across(rooms, room, door)
                    if other in stairs:
                        landings.add(id(room))
        for unit, room, c, other in _entries(rooms, False):
            if other in stairs or id(other) in landings:
                continue
            blocking.append({'code': 'PLOT_ENTRY_NOT_ON_LANDING', 'room_ref': [template, room.get('id')],
                             'severity': 'error', 'message': _label(template, room) + 'مدخل الشقة ' + str(unit)
                             + ' يفتح على ' + ('ممر مشترك' if other and other.get('role') == 'corridor' else 'فراغ مشترك')
                             + ' وليس على بسطة الدرج كما طلبت. افتح الشقة مباشرة على ردهة الدرج.' + _where(indices)})


def _dead_ends(building, rules, advisory):
    if rules.get('dwelling') == VILLA:
        return
    for template, indices in _groups(building, 'upper'):
        rooms = _rooms(building, template)
        common = [r for r in rooms if not r.get('unit_id') and r.get('role') in ('corridor', 'lobby', 'entrance', 'landing')]
        for room in common:
            x, z, w, d = room['rect']
            axis = 0 if w >= d else 1
            start, end = (x, x + w) if axis == 0 else (z, z + d)
            useful, leaves = [], []
            for door in room.get('doors') or []:
                if not isinstance(door, dict) or door.get('edge') not in _OUT:
                    continue
                other, c = _across(rooms, room, door)
                if c is None:
                    continue
                if other is not None and (other.get('unit_id') or other.get('role') in ('stairs', 'stair', 'elevator')):
                    useful.append(c[axis])
                elif other is not None and other in common:
                    leaves.append((c[axis], other))
            if not useful:
                continue
            lo, hi = min(useful), max(useful)
            run = 0.0
            for edge_pos, gap in ((start, lo - start), (end, end - hi)):
                extra = sum(max(o['rect'][2], o['rect'][3]) for pos, o in leaves
                            if abs(pos - edge_pos) <= 1.0 and not any(
                                (u.get('unit_id') or u.get('role') in ('stairs', 'stair', 'elevator'))
                                for u in (_across(rooms, o, dd)[0] for dd in o.get('doors') or []
                                          if isinstance(dd, dict) and dd.get('edge') in _OUT) if u is not None))
                run = max(run, gap + extra)
            if run > DEAD_END_MAX_M + EPS:
                advisory.append({'code': 'PLOT_DEAD_END_CORRIDOR', 'room_ref': [template, room.get('id')],
                                 'severity': 'advisory', 'message': _label(template, room) + 'ممر مشترك مسدود النهاية بطول نحو '
                                 + _fmt(run) + ' م بعد آخر باب شقة أو درج (المرجع المقترح ' + _fmt(DEAD_END_MAX_M)
                                 + ' م، غير متحقق من كود الحريق). اختصره أو اجعل الشقق على بسطة الدرج.' + _where(indices)})


def _unit_areas(building, rules, advisory):
    target = rules.get('unit_area_target_m2')
    if not _num(target) or target <= 0:
        return
    tol = rules.get('unit_area_tolerance', UNIT_AREA_TOLERANCE)
    for template, indices in _groups(building):
        areas = {}
        for room in _rooms(building, template):
            if isinstance(room.get('unit_id'), str) and room['unit_id']:
                areas[room['unit_id']] = areas.get(room['unit_id'], 0.0) + room['rect'][2] * room['rect'][3]
        off = {u: a for u, a in areas.items() if abs(a - target) > target * tol + EPS}
        if off:
            first = next(r for r in _rooms(building, template) if r.get('unit_id') == next(iter(off)))
            advisory.append({'code': 'PLOT_UNIT_AREA_OFF_TARGET', 'room_ref': [template, first.get('id')],
                             'severity': 'advisory', 'message': _label(template, first) + 'مساحات الشقق '
                             + '، '.join(str(u) + ' ≈ ' + _fmt(a) + ' م²' for u, a in sorted(off.items()))
                             + ' خارج الهدف ' + _fmt(target) + ' م² ±' + _fmt(tol * 100) + '٪ من تقدير الخيار المختار.' + _where(indices)})


def check(building, rules):
    """Return (blocking, advisory) findings for a revision with plot rules.

    Hard rules block approval: rooms outside the envelope, coverage, openings
    on a neighbour's plot line, parking shortfall, upper external doors, and
    landing entries / guest zoning when the brief explicitly asked for them.
    """
    blocking, advisory = [], []
    rules = usable(rules)
    if rules is None:
        return [{'code': 'PLOT_RULES_INVALID', 'severity': 'error',
                 'message': 'بيانات اشتراطات الأرض في هذه النسخة غير صالحة؛ أعد التوليد من بيانات الأرض.'}], []
    levels = _occupied(building)
    env = rules['envelope']
    for template, indices in _groups(building):
        out = [r for r in _rooms(building, template) if not _inside(r['rect'], env)]
        if out:
            blocking.append({'code': 'PLOT_OUTSIDE_ENVELOPE', 'room_ref': [template, out[0].get('id')], 'severity': 'error',
                             'message': _label(template, out[0]) + str(len(out)) + ' من الفراغات خارج المساحة القابلة للبناء '
                             '(x من ' + _fmt(env[0]) + ' إلى ' + _fmt(env[0] + env[2]) + '، z من ' + _fmt(env[1]) + ' إلى '
                             + _fmt(env[1] + env[3]) + ') — داخل الارتدادات: ' + '، '.join(str(r.get('id')) for r in out[:6])
                             + ('…' if len(out) > 6 else '') + '.' + _where(indices)})
    land = rules['land']['w'] * rules['land']['d']
    footprint = max([sum(r['rect'][2] * r['rect'][3] for r in _rooms(building, l['template'])) for l in levels] or [0])
    if footprint > rules['max_coverage'] * land + 1e-6:
        blocking.append({'code': 'PLOT_COVERAGE_EXCEEDED', 'severity': 'error',
                         'message': 'مساحة الدور ' + _fmt(footprint) + ' م² = ' + _fmt(footprint / land * 100)
                         + '٪ من الأرض، أكثر من نسبة البناء ' + _fmt(rules['max_coverage'] * 100) + '٪.'})
    _openings(building, rules, blocking, advisory)
    park = rules['parking']
    if park.get('placement') == 'none':
        if park.get('regulatory_default'):
            advisory.append({'code': 'PLOT_PARKING_NOT_PROVIDED', 'severity': 'advisory',
                             'message': 'لا مواقف في هذا المقترح باختيارك؛ الاشتراط الافتراضي '
                             + str(park['regulatory_default']) + ' مواقف داخل حدود الملكية.'})
    elif park.get('required'):
        capacity = parking_capacity(building, rules)
        if capacity < park['required']:
            where = 'الارتداد الأمامي' if park['placement'] == 'front_setback' else 'مواقف الدور الأرضي'
            blocking.append({'code': 'PLOT_PARKING_SHORTFALL', 'severity': 'error',
                             'message': 'المواقف المطلوبة ' + str(park['required']) + ' ويتسع ' + where + ' في هذا المخطط لـ '
                             + str(capacity) + ' فقط' + (' (عمق الارتداد أمام المبنى أقل من ' + _fmt(STALL_D) + ' م أو الواجهة لا تكفي)'
                                                         if park['placement'] == 'front_setback' else '') + '.'})
    _upper_doors(building, blocking, advisory)
    if levels and rules.get('dwelling') == APARTMENTS:
        ground_rooms = _rooms(building, levels[0]['template'])
        door_sides = {d.get('edge') for r in ground_rooms if not r.get('unit_id') and r.get('role') in ('entrance', 'lobby')
                      for d in r.get('doors') or [] if isinstance(d, dict) and d.get('edge') in _OUT
                      and _across(ground_rooms, r, d)[0] is None}
        if door_sides and not door_sides & set(rules['streets']):
            advisory.append({'code': 'PLOT_ENTRANCE_NOT_ON_STREET', 'severity': 'advisory',
                             'message': 'باب مدخل العمارة لا يطل على الشارع (' + '، '.join(SIDE_AR[s] for s in rules['streets']) + ').'})
    _landing(building, rules, blocking, advisory)
    _dead_ends(building, rules, advisory)
    _unit_areas(building, rules, advisory)
    _zoning(building, rules, blocking, advisory)
    return blocking[:128], advisory[:128]


def summary(building, rules):
    """Compact drawing data for the review UI (no authority)."""
    rules = usable(rules)
    if rules is None:
        return None
    park = rules['parking']
    return {'land': rules['land'], 'streets': rules['streets'], 'setbacks_m': rules['setbacks_m'],
            'envelope': rules['envelope'], 'max_coverage': rules['max_coverage'],
            'parking': {'placement': park.get('placement'), 'required': park.get('required'),
                        'stalls': stalls(building, rules)[:200]}}
