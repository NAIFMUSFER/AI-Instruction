# -*- coding: utf-8 -*-
"""فحوص أمن الخادم والتهيئة — تعمل من أي مجلّد: كل المسارات تُحلّ نسبةً إلى
جذر المستودع، فلا تعتمد على أي ملفّ مؤقّت."""
import re, os, sys, json
_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_HERE))


def _open(rel, *a, **k):
    return open(os.path.join(ROOT, rel), *a, **k)


p=[0]; f=[0]
def chk(n,c,d=''):
    if c: p[0]+=1; print('  ✓',n)
    else: f[0]+=1; print('  ✗',n,d)
api=_open('acs_understand_api.py',encoding='utf-8').read()
nt=_open('netlify.toml',encoding='utf-8').read()
df=_open('Dockerfile',encoding='utf-8').read()
ry=_open('render.yaml',encoding='utf-8').read()
idx=_open('public/index.html',encoding='utf-8').read()

chk('S1 CORS مقيّد بأصول معلومة (لا *)',
    'allow_origins' in api and '"*"' not in re.search(r'allow_origins\s*=\s*\[[^\]]*\]|allow_origins=[^,\)]*', api).group(0),
    re.search(r'allow_origins[^\n]*', api).group(0)[:120])
chk('S2 حد معدّل الطلبات قائم', re.search(r'RATE|rate_limit|_BUCKET|too many', api, re.I) is not None)
chk('S3 لا مفتاح API مكتوب في الشيفرة',
    not re.search(r'sk-ant-[A-Za-z0-9\-_]{8,}|AKIA[0-9A-Z]{12,}', api+idx+df+ry+nt))
chk('S4 المفتاح يُقرأ من البيئة فقط', 'os.environ' in api or 'getenv' in api)
chk('S5 معرّف النموذج claude-sonnet-5 لم يتغيّر',
    'claude-sonnet-5' in df and 'claude-sonnet-5' in ry, 'Dockerfile/render.yaml')
chk('S6 CSP لا تحتوي script-src * ', "script-src *" not in nt and "default-src *" not in nt)
chk('S7 رؤوس الأمان الأساسية موجودة',
    all(h in nt for h in ('Content-Security-Policy','X-Frame-Options','X-Content-Type-Options','Referrer-Policy')))
chk('S8 connect-src يقتصر على الخادم المعلوم',
    "connect-src 'self' https://acs-engine.onrender.com" in nt)
chk('S9 الرسائل لا تطبع أسراراً', not re.search(r'print\([^)]*(api_key|API_KEY|token)', api))
# عزل الصناعي متطابق بايت-بايت
# المجال الصناعي: نفس الكلمات الأربع الإنجليزية في الملفات الثلاثة
files=['acs_validate.py','acs_layout.py','acs_compiler.py']
dom={}
for fn in files:
    t=_open(fn,encoding='utf-8').read()
    m=re.search(r'\(\s*"warehouse"[^)]*\)', t)
    dom[fn]=re.findall(r'"([a-z]+)"', m.group(0)) if m else []
base=['warehouse','industrial','factory','logistics']
chk('S10 المجال الصناعي (الكلمات الأربع) متطابق في الثلاثة',
    all(d==base for d in dom.values()), dom)
# فرق موروث معروف: acs_validate يقبل مرادفاً عربياً إضافياً غير قابل للوصول عملياً
extra={fn:[w for w in re.findall(r'"([^"]+)"', re.search(r'\(\s*"warehouse"[^)]*\)', _open(fn,encoding='utf-8').read()).group(0)) if w not in base] for fn in files}
chk('S10b الفرق الموروث موثّق وغير قابل للوصول (btype إنجليزي فقط)',
    extra['acs_layout.py']==[] and extra['acs_compiler.py']==[] and extra['acs_validate.py']==['مستودع'],
    extra)
# Dockerfile يشمل كل الوحدات المستوردة
mods=re.findall(r'^import (acs_\w+)|^from (acs_\w+)', api+'\n'+_open('acs_egress.py',encoding='utf-8').read(), re.M)
need=set(['acs_understand','acs_understand_api','acs_validate','acs_layout','acs_programs','acs_project',
          'acs_relations','acs_navigation','acs_egress','acs_distance','acs_rules','acs_ingest','acs_occupancy','acs_revision'])
missing=[m for m in sorted(need) if (m+'.py') not in df]
chk('S11 Dockerfile ينسخ كل وحدات التشغيل', not missing, missing)
chk('S12 acs_programs.json منسوخ', 'acs_programs.json' in df)
chk('S13 acs_rules.json منسوخ', 'acs_rules.json' in df)
rules=_open('acs_rules.py',encoding='utf-8').read()
rjson=_open('acs_rules.json',encoding='utf-8').read()
chk('S14 محرّك القواعد بلا eval/exec/Function', not re.search(r'\beval\s*\(|\bexec\s*\(|compile\s*\(', rules))
# قوائم الحظر نفسها تحوي هذه السلاسل كنصّ بيانات؛ تُستبعد قبل الفحص
DENY = re.compile(r"(RULE_FORBIDDEN_KEYS|ING_FORBIDDEN|_FORBIDDEN(_KEYS)?)\s*=\s*[\[(][^\])]*[\])]", re.S)
# قوائم الحظر المعلنة داخل مواصفة JSON مضمّنة: النصوص هنا بيانات رفض لا شيفرة
DENY_JSON = re.compile(r'"(forbidden_value_patterns|forbidden_command_types|'
                       r'forbidden_payload_keys|reference_unsafe_patterns|'
                       r'unsafe_patterns|forbidden_prose_chars)"'
                       r'\s*:\s*\[[^\]]*\]', re.S)
def no_exec(text):
    t = DENY_JSON.sub('', DENY.sub('', text))
    # exec مسبوقاً بنقطة هو استدعاء دالّة على كائن (RegExp.prototype.exec) لا
    # تنفيذ ديناميكي — نفس المنطق المطبَّق أصلاً على eval بالضبط
    return not re.search(r'[^a-zA-Z_.]eval\s*\(|new\s+Function\s*\(|'
                         r'[^a-zA-Z_.]exec\s*\(|subprocess|os\.system|os\.popen', t)
chk('S15 نسخة المتصفّح من المحرّك بلا eval/new Function',
    no_exec(idx[idx.index('ACS_RULES_REGISTRY'):idx.index('ACS_INGEST_FIXTURES')]))
chk('S16 لا قيمة تنظيمية في سجلّ القواعد',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b', json.dumps(json.loads(rjson)['rulesets'])))
chk('S17 كل مصادر السجلّ NOT_LOADED وغير موثّقة',
    all(s0['status']=='NOT_LOADED' and s0['verified'] is False and s0['edition'] is None
        for s0 in json.loads(rjson)['sources'] if s0['source_id']!='synthetic_test'))
chk('S18 عدد القواعد التنظيمية = 0',
    sum(1 for rs0 in json.loads(rjson)['rulesets'] for r0 in rs0['rules'] if r0.get('regulatory') is True)==0)
chk('S19 acs_ingest.json منسوخ', 'acs_ingest.json' in df)
ing=_open('acs_ingest.py',encoding='utf-8').read()
ijson=_open('acs_ingest.json',encoding='utf-8').read()
chk('S20 خط الاستيراد بلا eval/exec/subprocess', no_exec(ing))
chk('S21 نسخة المتصفّح من خط الاستيراد بلا eval/new Function',
    no_exec(idx[idx.index('ACS_INGEST_FIXTURES'):idx.index('سجل برامج أنواع المباني')]))
chk('S29 محرّك القواعد بايثون بلا تنفيذ ديناميكي', no_exec(rules))
ij=json.loads(ijson)
chk('S22 لا محتوى تنظيمي في تجهيزات الاستيراد',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|civil[ _]?defense', ijson, re.I))
chk('S23 لا رابط تنظيمي مُختلق في التجهيزات', 'http://' not in ijson and 'https://' not in ijson)
chk('S24 كل وثائق التجهيزات اصطناعية وغير رسمية',
    all(d['synthetic'] is True and d.get('official') is not True for d in ij['store']['documents']))
chk('S25 كل الوثائق تبدأ UNVERIFIED',
    all(d['verification']['status']=='UNVERIFIED' for d in ij['store']['documents']))
chk('S26 كل الحزم تبدأ DRAFT بلا قواعد',
    all(p0['verification']['status']=='DRAFT' and not p0['candidate_ids'] for p0 in ij['store']['rulepacks']))
chk('S27 لا مرشّح مشحون بحالة VERIFIED',
    all(c0['status']!='VERIFIED' and c0['verification'] is None for c0 in ij['store']['candidates']))
sj=json.loads(_open('acs_sources.json',encoding='utf-8').read())
chk('S30 acs_sources.json منسوخ في الحاوية', 'acs_sources.json' in df)
chk('S31 سجلّ المصادر الحقيقية بلا نصّ بنود',
    not re.search(r'\bshall\b', json.dumps(sj), re.I))
chk('S32 لا مرشّحين ولا حِزَم في سجلّ المصادر الحقيقية',
    sj['candidates']==[] and sj['rulepacks']==[])
chk('S33 الوثيقة الحقيقية ليست CONTENT_VERIFIED',
    all(d0['verification']['status']!='CONTENT_VERIFIED' for d0 in sj['documents']))
chk('S34 كل شذرات السجلّ الحقيقي مواضع فهرس فقط',
    all(f0['kind']=='toc_locator' for f0 in sj['fragments']))
occ=_open('acs_occupancy.py',encoding='utf-8').read()
oj=json.loads(_open('acs_occupancy.json',encoding='utf-8').read())
chk('S35 acs_occupancy.json منسوخ في الحاوية', 'acs_occupancy.json' in df)
chk('S36 طبقة الإشغال بلا تنفيذ ديناميكي', no_exec(occ))
chk('S37 نسخة المتصفّح من طبقة الإشغال بلا eval/new Function',
    no_exec(idx[idx.index('ACS_OCCUPANCY_REGISTRY'):idx.index('سجل برامج أنواع المباني')]))
chk('S38 لا مجموعة إشغال حقيقية في حزم التصنيف',
    not re.search(r'\bSBC\b|\bIBC\b|Group [A-Z]-?[0-9]?\b', json.dumps(oj['packs'])))
chk('S39 كل حزم التصنيف اصطناعية وغير تنظيمية',
    all(p0['synthetic'] is True and p0['regulatory'] is False for p0 in oj['packs']))
chk('S40 كل حزم التصنيف تُشحن DRAFT',
    all(p0['verification']['status']=='DRAFT' for p0 in oj['packs']))
chk('S41 كل معرّفات التصنيف باسم TEST_OCC',
    all(c0['id'].startswith('TEST_OCC') for p0 in oj['packs'] for c0 in p0['classifications']))
rv=_open('acs_revision.py',encoding='utf-8').read()
rvj=json.loads(_open('acs_revision.json',encoding='utf-8').read())
chk('S43 acs_revision.json منسوخ في الحاوية', 'acs_revision.json' in df)
chk('S44 طبقة المراجعة بلا تنفيذ ديناميكي', no_exec(rv))
chk('S45 نسخة المتصفّح من طبقة المراجعة بلا eval/new Function',
    no_exec(idx[idx.index('ACS_REVISION_SPEC'):idx.index('سجل برامج أنواع المباني')]))
chk('S46 خوارزمية التجزئة sha256 ولا تشفير مُخترع', rvj['hash_algorithm']=='sha256')
chk('S47 لا محتوى تنظيمي في مواصفة المراجعة',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b', json.dumps(rvj)))
chk('S48 حالة العرض مستبعَدة صراحةً',
    all(k in rvj['volatile_keys'] for k in ('camera','ui','debug','session','cache')))
chk('S49 كل مسار حسّاس/غير حسّاس للترتيب موثّق بسبب',
    all(e.get('reason') for e in rvj['order_insensitive']+rvj['order_sensitive']))
chk('S42 سجل البرامج لم يتحوّل إلى سجلّ تصنيف نظامي',
    not re.search(r'TEST_OCC|occupancy', _open('acs_programs.json',encoding='utf-8').read(), re.I))
chk('S28 كل قاعدة مقترحة اصطناعية',
    all(c0['proposed_rule']['regulatory'] is False and c0['proposed_rule']['namespace']=='TEST_ONLY'
        for c0 in ij['store']['candidates']))
ar=_open('acs_arch.py',encoding='utf-8').read()
arj=json.loads(_open('acs_arch.json',encoding='utf-8').read())
chk('S50 acs_arch.json منسوخ في الحاوية', 'acs_arch.json' in df)
chk('S51 acs_arch.py منسوخ في الحاوية', 'acs_arch.py' in df)
chk('S52 مصرّف الهندسة بلا تنفيذ ديناميكي', no_exec(ar))
chk('S53 نسخة المتصفّح من مصرّف الهندسة بلا eval/new Function',
    no_exec(idx[idx.index('ACS_ARCH_SPEC'):idx.index('سجل برامج أنواع المباني')]))
chk('S54 لا محتوى تنظيمي في مواصفة الهندسة',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|civil.?defen', json.dumps(arj), re.I))
chk('S55 الاحتياطات معلنة كاحتياطات عرض لا كقيم هندسية',
    'RENDER FALLBACK' in arj['defaults_note'].upper())
chk('S56 قائمة الادّعاءات الممنوعة تغطي الإنشاء والحريق والمطابقة',
    all(k in arj['forbidden_claims'] for k in
        ('load_bearing','structural','fire_rated','compliant','code_required')))
chk('S57 لا ادّعاء إنشائي أو حريقي في شيفرة المصرّف',
    not re.search(r'load_bearing\s*=\s*True|fire_rated\s*=\s*True|structural["\']?\s*:\s*True', ar))
chk('S58 لا شبكة ولا نظام ملفات داخل المصرّف عدا قراءة مواصفته',
    ar.count('open(') == 1 and 'requests' not in ar and 'urllib' not in ar)
chk('S59 المصرّف لا يستورد أي محرّك قواعد أو إشغال',
    not re.search(r'import\s+acs_(rules|ingest|occupancy|egress|revision)', ar))
sr=_open('acs_struct.py',encoding='utf-8').read()
srj=json.loads(_open('acs_struct.json',encoding='utf-8').read())
chk('S60 acs_struct.json منسوخ في الحاوية', 'acs_struct.json' in df)
chk('S61 acs_struct.py منسوخ في الحاوية', 'acs_struct.py' in df)
chk('S62 طبقة النموذج الإنشائي بلا تنفيذ ديناميكي', no_exec(sr))
chk('S63 نسخة المتصفّح من الطبقة الإنشائية بلا eval/new Function',
    no_exec(idx[idx.index('ACS_STRUCT_SPEC'):idx.index('سجل برامج أنواع المباني')]))
chk('S64 لا كود إنشائي في المواصفة',
    not re.search(r'\bSBC\b|\bIBC\b|\bACI\b|\bASCE\b|\bAISC\b|Eurocode', json.dumps(srj), re.I))
chk('S65 DESIGNED/SAFE/COMPLIANT ليست حالات نموذج',
    all(x not in srj['model_status'] for x in ('DESIGNED','SAFE','COMPLIANT')))
chk('S66 UNSAFE/DANGEROUS ليست شدّات', srj['issue_severities']==['INFO','WARNING','ERROR'])
chk('S67 rule ليست مصدر إسناد إنشائي', 'rule' not in srj['provenance_values'])
chk('S68 احتياط العرض معلن كاحتياط لا كتصميم',
    'DISPLAY GEOMETRY IS NOT STRUCTURAL DESIGN' in srj['display_fallback_note'])
chk('S69 الادّعاءات الممنوعة تغطي الأحمال والتسليح والكفاية',
    all(k in srj['forbidden_claims'] for k in
        ('dead_load','live_load','wind_load','seismic_load','reinforcement',
         'structurally_safe','structurally_adequate','compliant')))
chk('S70 لا حساب أحمال في شيفرة الطبقة الإنشائية',
    not re.search(r'def .*(load|moment|shear|capacity|deflect|rebar|reinforc)', sr, re.I))
chk('S71 الطبقة الإنشائية لا تستورد محرّك قواعد أو إشغال',
    not re.search(r'import\s+acs_(rules|ingest|occupancy|egress|revision|navigation)', sr))
chk('S72 لا شبكة داخل الطبقة الإنشائية',
    'requests' not in sr and 'urllib' not in sr and sr.count('open(') == 1)
chk('S73 مواصفة المراجعة تستبعد إظهار الطبقات من البصمة',
    all(k in json.loads(_open('acs_revision.json',encoding='utf-8').read())['volatile_keys']
        for k in ('layer_visibility','visible_layers')))
mp=_open('acs_mep.py',encoding='utf-8').read()
mj=json.loads(_open('acs_mep.json',encoding='utf-8').read())
chk('S74 acs_mep.json منسوخ في الحاوية', 'acs_mep.json' in df)
chk('S75 acs_mep.py منسوخ في الحاوية', 'acs_mep.py' in df)
chk('S76 طبقة MEP بلا تنفيذ ديناميكي', no_exec(mp))
chk('S77 نسخة المتصفّح من طبقة MEP بلا eval/new Function',
    no_exec(idx[idx.index('ACS_MEP_SPEC'):idx.index('سجل برامج أنواع المباني')]))
chk('S78 لا معيار MEP في المواصفة',
    not re.search(r'\bSBC\b|\bNFPA\b|\bNEC\b|\bIEC\b|ASHRAE|SMACNA|\bIPC\b',
                  json.dumps(mj).replace('meets_nfpa','').replace('meets_nec','')
                  .replace('meets_ashrae','')))
chk('S79 DESIGNED/COMPLIANT/ADEQUATE/BALANCED/CALCULATED ليست حالات نموذج',
    all(x not in mj['model_status'] for x in
        ('DESIGNED','COMPLIANT','ADEQUATE','BALANCED','CALCULATED')))
chk('S80 UNSAFE/VIOLATION ليست شدّات', mj['issue_severities']==['INFO','WARNING','ERROR'])
chk('S81 OPTIMIZED ليست حالة توجيه', 'OPTIMIZED' not in mj['routing_statuses'])
chk('S82 rule/code_required ليست مصادر إسناد',
    'rule' not in mj['provenance_values'] and 'code_required' not in mj['provenance_values'])
chk('S83 احتياط العرض معلن كاحتياط لا كقيمة هندسية',
    'DISPLAY VALUE IS NOT AN ENGINEERING VALUE' in mj['display_fallback_note'])
chk('S84 الادّعاءات الممنوعة تغطي الأحمال والتدفّق والهيدروليك والمطابقة',
    all(k in mj['forbidden_claims'] for k in
        ('design_load','voltage_drop','cable_size','cooling_load','airflow_cfm',
         'fixture_units','pump_head','sprinkler_density','hydraulic_calculation','compliant')))
chk('S85 لا دوال حساب أحمال/تدفّق/تحجيم في الشيفرة',
    not re.search(r'def .*(load|airflow|flow_rate|sizing|size_pipe|size_duct|hydraul|lux)',
                  mp, re.I))
chk('S86 لا محرّك حريق: المواصفة تنفيه صراحةً',
    'There is no Fire / Life-Safety engine' in mj['fire_note'])
chk('S87 محوّل المرحلة 1 لا يستطيع كتابة code_required', 'code_required' not in mp)
chk('S88 طبقة MEP لا تستورد محرّك قواعد أو إشغال',
    not re.search(r'import\s+acs_(rules|ingest|occupancy|egress|revision|navigation)', mp))
chk('S89 لا شبكة داخل طبقة MEP',
    'requests' not in mp and 'urllib' not in mp and mp.count('open(') == 1)
chk('S90 MEP ليست عائقاً للملاحة في هذه المرحلة',
    'NOT navigation obstacles in this phase' in mj['navigation_note'])
fl=_open('acs_fls.py',encoding='utf-8').read()
fj=json.loads(_open('acs_fls.json',encoding='utf-8').read())
_fj_core=json.dumps({k:v for k,v in fj.items()
                     if k not in ('note','fire_note','forbidden_provenance','forbidden_claims',
                                  'provenance_note','severity_note','occupancy_note')})
chk('S91 acs_fls.json منسوخ في الحاوية', 'acs_fls.json' in df)
chk('S92 acs_fls.py منسوخ في الحاوية', 'acs_fls.py' in df)
chk('S93 طبقة الحريق بلا تنفيذ ديناميكي', no_exec(fl))
chk('S94 نسخة المتصفّح من طبقة الحريق بلا eval/new Function',
    no_exec(idx[idx.index('ACS_FLS_SPEC'):idx.index('سجل برامج أنواع المباني')]))
chk('S95 لا قيمة كود حريق في المواصفة (خارج قوائم المنع ونصوص النفي)',
    not re.search(r'\bNFPA\b|\bIBC\b|civil.?defen', _fj_core, re.I))
chk('S96 COMPLIANT/SAFE/APPROVED/CERTIFIED/DESIGNED ليست حالات نموذج',
    all(x not in fj['model_status'] for x in
        ('COMPLIANT','SAFE','APPROVED','CERTIFIED','DESIGNED')))
chk('S97 UNSAFE/VIOLATION ليست شدّات', fj['issue_severities']==['INFO','WARNING','ERROR'])
chk('S98 code_required و rule ليستا مصدري إسناد',
    'code_required' not in fj['provenance_values'] and 'rule' not in fj['provenance_values'])
chk('S99 code_required معلنة صراحةً كإسناد ممنوع',
    'code_required' in fj['forbidden_provenance'] and 'rule' in fj['forbidden_provenance'])
chk('S100 لا حساب تغطية/تباعد/هيدروليك في الشيفرة',
    not re.search(r'def .*(coverage|spacing|hydraul|density|k_factor|audib|candela)', fl, re.I))
chk('S101 المواصفة تنفي وجود محرّك حريق/سلامة صراحةً',
    'There is no Fire / Life-Safety engine' in fj['fire_note'])
chk('S102 الغياب ليس مخالفة — معلن في المواصفة',
    'absence is not a violation without a verified rule' in fj['severity_note'])
chk('S103 طبقة الحريق لا تستورد محرّك قواعد أو إشغال',
    not re.search(r'import\s+acs_(rules|ingest|occupancy|revision|struct)', fl))
chk('S104 لا شبكة داخل طبقة الحريق',
    'requests' not in fl and 'urllib' not in fl and fl.count('open(') == 1)
chk('S105 الحريق ليس عائقاً للملاحة ولا يغيّر الإخلاء',
    'NOT navigation obstacles' in fj['navigation_note'])
cd=_open('acs_coord.py',encoding='utf-8').read()
cj=json.loads(_open('acs_coord.json',encoding='utf-8').read())
_cj_core=json.dumps({k:v for k,v in cj.items() if not k.endswith('note')
                     and k!='forbidden_claims'})
chk('S121 acs_coord.json منسوخ في الحاوية', 'acs_coord.json' in df)
chk('S122 acs_coord.py منسوخ في الحاوية', 'acs_coord.py' in df)
chk('S123 طبقة التنسيق بلا تنفيذ ديناميكي', no_exec(cd))
chk('S124 نسخة المتصفّح من طبقة التنسيق بلا eval/new Function',
    no_exec(idx[idx.index('ACS_COORD_SPEC'):idx.index('ACS_FLS_SPEC')]))
chk('S125 لا قيمة كود في مواصفة التنسيق (خارج قوائم المنع ونصوص النفي)',
    not re.search(r'\bNFPA\b|\bIBC\b|\bSBC\b|\bASHRAE\b|\bNEC\b|civil.?defen',
                  _cj_core, re.I))
chk('S126 UNSAFE/FATAL/VIOLATION ليست شدّات', cj['severities']==['INFO','WARNING','ERROR'])
chk('S127 RESOLVED ليست حالة تلقائية', 'RESOLVED' not in cj['clash_statuses'])
chk('S128 مفردات الإصلاح التلقائي معلنة ممنوعة',
    all(w in cj['forbidden_claims'] for w in
        ('auto_fixed','rerouted','resized','resolved_automatically','opening_created')))
chk('S129 لا مولّد حلول ولا توجيه ولا تحجيم في الشيفرة',
    not re.search(r'def .*(reroute|resize|optimi[sz]e|generate_opening|create_sleeve|auto_fix)',
                  cd, re.I))
chk('S130 طبقة التنسيق لا تكتب في أي نموذج تخصّص',
    'the coordination model is DERIVED' in cj['derivation_note'])
chk('S131 التنسيق لا يستورد محرّك قواعد أو إشغال أو إخلاء',
    not re.search(r'import\s+acs_(rules|ingest|occupancy|egress|navigation|distance)', cd))
chk('S132 لا شبكة داخل طبقة التنسيق',
    'requests' not in cd and 'urllib' not in cd and cd.count('open(') == 1)
chk('S133 التنسيق لا يغيّر الملاحة ولا الإخلاء في هذه المرحلة',
    'do NOT affect navigation, egress, pathfinding or walking distance'
    in cj['navigation_note'])
chk('S134 اللقطة تُصدَّر عند الطلب فقط ولا تُدمَج في التصدير العادي',
    'never persisted as core model ' in cd and 'truth; it is never' not in cd
    and 'def export_snapshot' in cd)
chk('S135 علامة التصحيح لا تُخبز في تصدير GLB',
    'COORD_DEBUG_MARKER' in idx and 'acs_debug_only' in idx
    and 'new GLTFExporter().parse(model' in idx)
vd=_open('acs_visual.py',encoding='utf-8').read()
vj=json.loads(_open('acs_visual.json',encoding='utf-8').read())
_vj_core=json.dumps({k:v for k,v in vj.items() if not k.endswith('note')
                     and k not in ('forbidden_claims','ai_may_not_change','mode_intent')})
chk('S137 acs_visual.json منسوخ في الحاوية', 'acs_visual.json' in df)
chk('S138 acs_visual.py منسوخ في الحاوية', 'acs_visual.py' in df)
chk('S139 طبقة العرض البصري بلا تنفيذ ديناميكي', no_exec(vd))
chk('S140 نسخة المتصفّح من طبقة العرض بلا eval/new Function',
    no_exec(idx[idx.index('ACS_VISUAL_SPEC'):idx.index('ACS_COORD_SPEC')]))
chk('S141 لا قيمة كود في مواصفة العرض البصري',
    not re.search(r'\bNFPA\b|\bIBC\b|\bSBC\b|\bASHRAE\b|\bADA\b|civil.?defen',
                  _vj_core, re.I))
chk('S142 المادة البصرية مصنّفة VISUAL_MATERIAL فقط',
    vj['material_class'] == 'VISUAL_MATERIAL')
chk('S143 لا خاصية حريق أو حرارية أو إنشائية في مكتبة المواد',
    all(not any(k in m for k in ('fire_rating','thermal','u_value','strength',
                                 'reaction_to_fire'))
        for m in vj['materials'].values()))
chk('S144 الديكور مصنّف VISUAL_DECORATION ولا يُحتسب هندسياً',
    vj['decoration_class'] == 'VISUAL_DECORATION'
    and 'decoration_is_engineering_object' in vj['forbidden_claims'])
chk('S145 صورة الذكاء الاصطناعي لا تُعتمد نموذجاً هندسياً',
    vj['render_authority']['AI_ENHANCED_VISUALISATION'] == 'VISUALISATION'
    and 'ai_generated_geometry' in vj['forbidden_claims'])
chk('S146 الذكاء الاصطناعي ممنوع من تغيير أي سمة تخطيط',
    all(k in vj['ai_may_not_change'] for k in
        ('wall_positions','door_count','window_count','floor_count','stair_location',
         'building_footprint','room_count')))
chk('S147 لا مولّد صور ولا شبكة داخل طبقة العرض',
    'requests' not in vd and 'urllib' not in vd and vd.count('open(') == 1
    and not re.search(r'def .*(generate_image|diffusion|txt2img|call_api)', vd, re.I))
chk('S148 لا مولّد هندسة ولا عملية تصميم في طبقة العرض',
    not re.search(r'def .*(create_room|move_wall|add_door|delete_room|redesign|'
                  r'generate_geometry)', vd, re.I))
chk('S149 لا اعتماد CDN جديد للقوام: المواد وسيطيّة محليّة',
    'https://' not in vd and 'http://' not in vd
    and 'no remote CDN texture is required' in vj['texture_note'])
chk('S150 بيانات الأصل لا تُنفَّذ: الحقول التي تحمل شيفرة تُرفض',
    'ASSET_METADATA_MUST_NOT_CARRY_CODE' in vd)
chk('S151 الأصل مجهول الرخصة لا يُبَثّ في أي مشهد',
    'ASSET_LICENSE_UNKNOWN_NOT_EMITTED' in vd and 'UNKNOWN' in vj['asset_licenses'])
chk('S152 حالة التقديم لا تدخل بصمة المراجعة',
    'affects_revision_hash' in vd and vj['presentation_block_key'] == 'presentation')
chk('S153 الأجسام البصرية خارج مجموعة المبنى فلا تدخل تصدير GLB الهندسي',
    "VIS_GROUP.name='VISUAL_ONLY'" in idx and 'acs_visual_only' in idx
    and 'scene.add(VIS_GROUP)' in idx and 'new GLTFExporter().parse(model' in idx)
chk('S154 العرض الهندسي لا يخفي أي تخصّص',
    'ENGINEERING_VIEW_MUST_NOT_HIDE_A_DISCIPLINE' in vd)
chk('S155 مقياس الواقع الافتراضي 1:1 ولا يتغيّر صامتاً',
    'one model metre is one physical metre' in vj['vr_scale_note']
    and 'scale_is_explicit' in vd)
chk('S136 لا مسافة انتقال نظامية', 'no fire-code travel distance exists' in fj['distance_note'])
# ---------------------------------------------------------------- المرحلة 5
au = _open('acs_authoring.py', encoding='utf-8').read()
auj = json.loads(_open('acs_authoring.json', encoding='utf-8').read())
chk('S-A1 طبقة التأليف بايثون بلا تنفيذ ديناميكي', no_exec(au))
chk('S-A2 نسخة المتصفّح من طبقة التأليف بلا eval/new Function',
    no_exec(idx[idx.index('ACS AUTHORING LAYER'):idx.index('END ACS AUTHORING LAYER')]))
chk('S-A3 فحص التنفيذ الديناميكي غير عقيم', not no_exec('x = eval("1+1")'))
chk('S-A4 مفاتيح تلويث النموذج الأولي معلنة ومرفوضة',
    '__proto__' in auj['forbidden_payload_keys']
    and 'constructor' in auj['forbidden_payload_keys'])
chk('S-A5 لا نوع أمر يكتب بمسار حرّ',
    all(t in auj['forbidden_command_types']
        for t in ('SET_ANY_FIELD', 'PATCH_OBJECT', 'RAW_JSON_MUTATION')))
chk('S-A6 حدّ الإحداثيات معلن ومنتهٍ',
    0 < float(auj['limits']['max_abs_coordinate_m']) < float('inf'))
chk('S-A7 حدّ حجم المعاملة معلن', int(auj['limits']['max_commands_per_transaction']) > 0)
chk('S-A8 التأليف لا يدّعي مطابقة أنظمة', auj['compliance_status'] == 'NOT_EVALUATED')
chk('S-A9 سجلّ التدقيق يستبعد الأسرار وسلاسل التفكير',
    'never records a secret' in auj['audit_note']
    and 'chain-of-thought' in auj['audit_note'])
chk('S-A10 لا مسار كتابة من زمن التشغيل إلى النموذج',
    'RUNTIME_MODEL_WRITE_ATTEMPT' in auj['runtime_boundary_note'])

# ---------------------------------------------------------------- المرحلة 6
ws = _open('acs_workspace.py', encoding='utf-8').read()
wsj = json.loads(_open('acs_workspace.json', encoding='utf-8').read())
WSB = '/* ===== ACS WORKSPACE UI (generated by tools/build_workspace_ui.py) ===== */'
WSE = '/* ===== END ACS WORKSPACE UI ===== */'
chk('S-W1 طبقة مساحة العمل بايثون بلا تنفيذ ديناميكي', no_exec(ws))
chk('S-W2 كتلة الواجهة المولَّدة موجودة مرّة واحدة بالضبط',
    idx.count(WSB) == 1 and idx.count(WSE) == 1)
wsblock = idx[idx.index(WSB):idx.index(WSE)]
chk('S-W3 نسخة المتصفّح من مساحة العمل بلا eval/new Function', no_exec(wsblock))
chk('S-W4 فحص التنفيذ الديناميكي غير عقيم على كتلة الواجهة',
    not no_exec(wsblock + '\nvar x = eval("1+1");'))
chk('S-W5 قائمة أنماط المراجع غير الآمنة معلنة في المواصفة',
    len(wsj['reference_unsafe_patterns']) >= 10
    and 'javascript:' in wsj['reference_unsafe_patterns']
    and '<script' in wsj['reference_unsafe_patterns'])
chk('S-W6 الواجهة لا تكتب في النموذج الهندسي',
    wsj['model_hash_inputs'] == ['model'])
chk('S-W7 مساحة العمل لا تدّعي مطابقة أنظمة',
    wsj['accessibility']['claims_formal_compliance'] is False)
chk('S-W8 كلمات الحالة الممنوعة معلنة',
    len(wsj['forbidden_status_words']) > 0
    and any(w.lower() == 'compliant' for w in wsj['forbidden_status_words']))
chk('S-W9 تسميات المصدر الممنوعة معلنة',
    len(wsj['forbidden_provenance_labels']) >= 5)
chk('S-W10 لا حفظ سحابي مُدّعى', wsj['persistence']['cloud'] is False)
chk('S-W11 خطّ العرض الواقعي معلن غير منفَّذ',
    wsj['photorealistic_implemented'] is False)
chk('S-W12 الواجهة لا تُنشئ رابطاً برمجياً خطيراً',
    not re.search(r"=\s*['\"]javascript:", wsblock)
    and 'document.write(' not in wsblock)
chk('S-W13 نصوص الواجهة تُقرأ من المواصفة لا من جدول ثانٍ',
    'ACS_WORKSPACE_SPEC.ui_labels' in wsblock
    and len(wsj['ui_labels']) > 40)
chk('S-W14 كل نصّ واجهة معرَّف في اللغتين',
    all(set(v.keys()) == {'ar', 'en'} and v['ar'] and v['en']
        for v in wsj['ui_labels'].values()))
chk('S-W15 حالة الواجهة مصنَّفة ولا تدخل بصمة النموذج',
    'UI_STATE' in wsj['state_classes']
    and all(k in wsj['state_ownership'] for k in ('selected_id', 'ui_mode')))

# ---------------------------------------------------------------- المرحلة 7
rd = _open('acs_render.py', encoding='utf-8').read()
rdj = json.loads(_open('acs_render.json', encoding='utf-8').read())
RB = '/* ===== ACS RENDER ENGINE (generated by tools/build_render_browser.py) ===== */'
RE = '/* ===== END ACS RENDER ENGINE ===== */'
chk('S-R1 طبقة العرض بايثون بلا تنفيذ ديناميكي', no_exec(rd))
chk('S-R2 كتلة العرض المولَّدة موجودة مرّة واحدة بالضبط',
    idx.count(RB) == 1 and idx.count(RE) == 1)
rdblock = idx[idx.index(RB):idx.index(RE)]
chk('S-R3 نسخة المتصفّح من طبقة العرض بلا eval/new Function', no_exec(rdblock))
chk('S-R4 فحص التنفيذ الديناميكي غير عقيم على كتلة العرض',
    not no_exec(rdblock + '\nvar x = eval("1+1");'))
chk('S-R5 لا كتابة عكسية من صورة إلى نموذج',
    rdj['reverse_write_allowed'] is False and rdj['writes_to_model'] is False
    and rdj['model_hash_inputs'] == ['model'])
chk('S-R6 مخرج الذكاء الاصطناعي بلا سلطة هندسية',
    rdj['ai_engineering_authority'] is False)
chk('S-R7 لا مولّد واقعية مشحون', rdj['photorealistic_engine_shipped'] is False)
chk('S-R8 مفتاح المزوّد في بيئة الخادم فقط',
    rdj['provider_secret_location'] == 'SERVER_ENVIRONMENT'
    and 'never appears in client source' in rdj['provider_secret_note'])
chk('S-R9 لا حقل بيانات وصفية يحمل سرّاً',
    not any(re.search(r'key|secret|token|password|credential', x, re.I)
            for x in rdj['metadata_fields']))
chk('S-R10 لا اسم مزوّد مثبَّت في المواصفة',
    not re.search(r'openai|stability|midjourney|replicate|anthropic',
                  json.dumps(rdj), re.I))
chk('S-R11 قوائم السماح معلنة للمعرّفات والمخطّطات والنصّ',
    isinstance(rdj['safe_id_pattern'], str)
    and 'https' in rdj['allowed_uri_schemes']
    and isinstance(rdj['visual_intent_pattern'], str))
chk('S-R12 حدود الحجم والبكسل معلنة ومنتهية',
    0 < rdj['max_reference_bytes'] < float('inf')
    and 0 < rdj['max_reference_pixels'] < float('inf')
    and 0 < rdj['max_render_px'] < float('inf')
    and 0 < rdj['buffer_max_px'] < float('inf'))
chk('S-R13 أنواع الصور المسموحة لا تشمل svg ولا html',
    all(m.startswith('image/') for m in rdj['allowed_image_mime'])
    and not any(re.search(r'svg|html|xml', m) for m in rdj['allowed_image_mime']))
chk('S-R14 كل مادّة مشحونة إجرائية وبرخصة معلنة',
    all(m['license'] == 'PROCEDURAL' and m['visual_only'] is True
        for m in rdj['material_library']))
chk('S-R15 لا مادّة تشير إلى مضيف بعيد',
    not any(str(t).startswith('http') for m in rdj['material_library']
            for t in (m.get('texture_refs') or [])))
chk('S-R16 المادّة البصرية لا تحمل خاصّية هندسية',
    not any(k in m for m in rdj['material_library']
            for k in ('fire_rating', 'structural_grade', 'u_value')))
chk('S-R17 لا نظام بناء مذكور في مواصفة العرض',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|\bACI\b|\bASCE\b|'
                  r'\bAISC\b|Eurocode|\bNEC\b|ASHRAE', json.dumps(rdj)))
chk('S-R18 لا تحليل شمسي مُدّعى', rdj['solar_analysis_claimed'] is False)
chk('S-R19 لا مخطّط تنفيذ مُدّعى', rdj['construction_drawing_claimed'] is False)
chk('S-R20 لوحة التصوير لا تعرض أي أداة تعديل هندسي',
    all(c in rdj['panel_forbidden_controls']
        for c in ('MOVE_WALL', 'MOVE_DOOR', 'RESIZE_SPACE', 'DELETE_SPACE')))
chk('S-R21 طبقة العرض لا تفتح اتصال شبكة',
    not re.search(r'urllib|requests|http\.client|socket', rd)
    and not re.search(r'\bfetch\s*\(|XMLHttpRequest|importScripts', rdblock))
chk('S-R22 مخازن التحكّم تُنقَّط على المعالج فلا تعتمد على بطاقة رسوميات',
    'CPU_DETERMINISTIC' in rd and 'gpu_dependent' in rd)
chk('S-R23 حالات التحقّق الأربع مفصولة',
    rdj['verification_classes'] == ['CODE_VERIFIED', 'RUNTIME_VERIFIED',
                                    'AI_VERIFIED', 'NOT_VERIFIED'])

# ---------------------------------------------------------------- المرحلة 8
def _walk_keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            for x in _walk_keys(v):
                yield x
    elif isinstance(node, list):
        for v in node:
            for x in _walk_keys(v):
                yield x


sys.path.insert(0, ROOT)
import acs_bim as _B                                              # noqa: E402
bm = _open('acs_bim.py', encoding='utf-8').read()
bmj = json.loads(_open('acs_bim.json', encoding='utf-8').read())
BB = '/* ===== ACS BIM EXCHANGE (generated by tools/build_bim_browser.py) ===== */'
BE = '/* ===== END ACS BIM EXCHANGE ===== */'
chk('S-B1 طبقة التبادل بايثون بلا تنفيذ ديناميكي', no_exec(bm))
chk('S-B2 كتلة التبادل المولَّدة موجودة مرّة واحدة بالضبط',
    idx.count(BB) == 1 and idx.count(BE) == 1)
bmblock = idx[idx.index(BB):idx.index(BE)]
chk('S-B3 نسخة المتصفّح من طبقة التبادل بلا eval/new Function', no_exec(bmblock))
chk('S-B4 فحص التنفيذ الديناميكي غير عقيم على كتلة التبادل',
    not no_exec(bmblock + '\nvar x = eval("1+1");'))
chk('S-B5 الثابت الملزم معلَن ولا يقبل التأويل',
    bmj['external_bim_is_model_truth'] is False
    and bmj['direct_import_write_allowed'] is False
    and bmj['requires_explicit_commit'] is True
    and bmj['writes_via_authoring_path'] is True)
chk('S-B6 لا جلب لأي مورد بعيد من ملفّ BIM',
    bmj['remote_dependency'] is False
    and bmj['remote_reference_policy'] == 'NEVER_FETCH'
    and bmj['allowed_external_reference_schemes'] == [])
chk('S-B7 طبقة التبادل لا تفتح اتصال شبكة',
    not re.search(r'urllib|requests|http\.client|socket', bm)
    and not re.search(r'\bfetch\s*\(|XMLHttpRequest|importScripts', bmblock))
# الطبقة تقرأ مواصفتها القانونية عند الاستيراد كبقيّة الطبقات، ولا شيء غيرها
chk('S-B8 طبقة التبادل لا تلمس نظام الملفّات إلا لقراءة مواصفتها',
    len(re.findall(r'\bopen\s*\(', bm)) == 1
    and 'acs_bim.json' in bm.split('open(')[1][:120]
    and not re.search(r'os\.remove|os\.unlink|shutil|pathlib|glob\.', bm))
chk('S-B9 لا نظام بناء مذكور في مواصفة التبادل',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|\bACI\b|\bASCE\b|'
                  r'\bAISC\b|Eurocode|\bNEC\b|ASHRAE', json.dumps(bmj)))
chk('S-B10 مادّة خارجية لا تُرقّى إلى مادّة هندسية',
    bmj['material_promotion_allowed'] is False
    and bmj['classification_authority'] is False
    and bmj['space_purpose_inference'] is False)
chk('S-B11 كل حدّ معلَن ومنتهٍ وموجب',
    all(isinstance(v, (int, float)) and 0 < v < float('inf')
        for v in bmj['limits'].values()))
chk('S-B12 قائمة سماح للمعرّفات معلَنة',
    isinstance(bmj['safe_id_pattern'], str) and bmj['safe_id_pattern'])
chk('S-B13 مفاتيح النموذج الأوّلي مرفوضة مفاتيحَ خاصّية',
    all(k in bmj['forbidden_property_keys']
        for k in ('__proto__', 'constructor', 'prototype')))
chk('S-B14 لوحة التبادل تمنع صراحةً كل طريق يتخطّى المراجعة والإيداع',
    all(c in bmj['panel_forbidden_controls']
        for c in ('IMPORT_AND_REPLACE_MODEL', 'APPLY_ALL_WITHOUT_REVIEW',
                  'AUTO_COMMIT_IMPORT', 'OVERWRITE_MODEL')))
chk('S-B15 لا أداة تعديل هندسي بين ضوابط لوحة التبادل',
    not any(re.search(r'MOVE_|RESIZE_|DELETE_|ADD_WALL|ADD_SPACE|EDIT_',
                      str(c)) for c in bmj['panel_controls']),
    json.dumps(bmj['panel_controls']))
# الفحص على أسماء المفاتيح لا على النثر: جملة "never secrets" في ملاحظة تدقيق
# ليست سرّاً، والاسم المفتاحي هو ما قد يحمل قيمة حسّاسة
chk('S-B22 لا مفتاح ولا سرّ في مواصفة التبادل',
    not any(re.search(r'api[_-]?key|secret|token|password|credential', k, re.I)
            for k in _walk_keys(bmj)))
chk('S-B16 مصدر أمر الاستيراد من مفردات المرحلة 5 لا اختراعاً',
    bmj['import_command_source']
    in json.loads(_open('acs_authoring.json', encoding='utf-8').read())
    ['command_sources'])
chk('S-B17 حالات التحقّق معلَنة ومفصولة',
    bmj['verification_classes'] == ['CODE_VERIFIED', 'RUNTIME_VERIFIED',
                                    'INTEROP_VERIFIED', 'NOT_VERIFIED'])

# حمولات BIM مشوّهة حقيقية تمرّ في المحلّل نفسه — لا نمذجة
_AT = '2026-01-01T00:00:00Z'
_H = ("ISO-10303-21;\nHEADER;\nFILE_DESCRIPTION((''),'2;1');\n"
      "FILE_NAME('t.ifc','1970-01-01T00:00:00',(''),(''),'','','');\n"
      "FILE_SCHEMA(('IFC4'));\nENDSEC;\nDATA;\n")
_T = "ENDSEC;\nEND-ISO-10303-21;\n"
_MAL = [
    ('empty file', ''),
    ('not a step file at all', '{"walls": []}'),
    ('json wearing an ifc name', '[{"a":1}]'),
    ('header only, no data section', _H.replace('DATA;\n', '')),
    ('unterminated string', _H + "#1=IFCSITE('a" + "\n" + _T),
    ('unterminated argument list', _H + "#1=IFCSITE('a',$,$\n" + _T),
    ('dangling reference', _H + "#1=IFCRELAGGREGATES('a',$,$,$,#999,(#998));\n" + _T),
    ('duplicate entity number', _H + "#1=IFCSITE('a',$,$,$,$,$,$,$,.ELEMENT.,$,$,$,$,$);\n"
                                     "#1=IFCSITE('b',$,$,$,$,$,$,$,.ELEMENT.,$,$,$,$,$);\n" + _T),
    ('non-finite numeric', _H + "#1=IFCCARTESIANPOINT((1.E999,0.,0.));\n" + _T),
    ('script in a name', _H + "#1=IFCSITE('a',$,'<script>x</script>',$,$,$,$,$,"
                              ".ELEMENT.,$,$,$,$,$);\n" + _T),
    ('external file reference', _H + "#1=IFCSITE('a',$,'file:///etc/passwd',$,$,$,$,$,"
                                     ".ELEMENT.,$,$,$,$,$);\n" + _T),
    ('deeply nested argument list', _H + "#1=IFCCARTESIANPOINT("
                                         + "(" * 200 + ")" * 200 + ");\n" + _T),
    ('over-long line', _H + "#1=IFCSITE('" + "a" * 2000000 + "');\n" + _T),
]
for _n, _txt in _MAL:
    try:
        _r = _B.stage_import(_txt, 'mal.ifc', {}, None, _AT)
        _crashed = False
    except Exception as _e:                                       # noqa: BLE001
        _r = None
        _crashed = True
    chk('S-B18 %s does not crash the parser' % _n, _crashed is False)
    if not _crashed:
        chk('S-B19 %s is refused or typed, never silently accepted' % _n,
            _r['valid'] is False or bool(_r['issues']),
            _n)
        chk('S-B20 %s writes nothing to any model' % _n,
            (_r['staging'] or {}).get('writes_to_model') is not True
            or _r['staging']['writes_to_model'] is False)
        chk('S-B21 %s reports only declared issue codes' % _n,
            all(i['code'] in bmj['issue_codes'] for i in _r['issues']),
            json.dumps(sorted(set(i['code'] for i in _r['issues']
                                  if i['code'] not in bmj['issue_codes'])))[:120])

# ---------------------------------------------------------------- المرحلة 9
import acs_docs as _D                                             # noqa: E402
dc = _open('acs_docs.py', encoding='utf-8').read()
dcj = json.loads(_open('acs_docs.json', encoding='utf-8').read())
DB = '/* ===== ACS DOCUMENTATION (generated by tools/build_docs_browser.py) ===== */'
DE = '/* ===== END ACS DOCUMENTATION ===== */'
chk('S-D1 طبقة التوثيق بايثون بلا تنفيذ ديناميكي', no_exec(dc))
chk('S-D2 كتلة التوثيق المولَّدة موجودة مرّة واحدة بالضبط',
    idx.count(DB) == 1 and idx.count(DE) == 1)
dcblock = idx[idx.index(DB):idx.index(DE)]
chk('S-D3 نسخة المتصفّح من طبقة التوثيق بلا eval/new Function', no_exec(dcblock))
chk('S-D4 فحص التنفيذ الديناميكي غير عقيم على كتلة التوثيق',
    not no_exec(dcblock + '\nvar x = eval("1+1");'))
chk('S-D5 التوثيق للقراءة فقط ولا يكتب إلى النموذج',
    dcj['documentation_is_read_only'] is True
    and dcj['writes_to_model'] is False
    and dcj['reverse_write_allowed'] is False
    and dcj['mutates_engineering_model'] is False)
chk('S-D6 طبقة التوثيق لا تفتح اتصال شبكة',
    not re.search(r'urllib|requests|http\.client|socket', dc)
    and not re.search(r'\bfetch\s*\(|XMLHttpRequest|importScripts', dcblock))
chk('S-D7 طبقة التوثيق لا تلمس نظام الملفّات إلا لقراءة مواصفتها',
    len(re.findall(r'\bopen\s*\(', dc)) == 1
    and 'acs_docs.json' in dc.split('open(')[1][:120]
    and not re.search(r'os\.remove|os\.unlink|shutil|pathlib|glob\.', dc))
chk('S-D8 لا نظام بناء مذكور في مواصفة التوثيق',
    not re.search(r'\bSBC\b|\bIBC\b|\bNFPA\b|\bADA\b|\bACI\b|\bASCE\b|'
                  r'\bAISC\b|Eurocode|\bNEC\b|ASHRAE', json.dumps(dcj)))
chk('S-D9 لا ادّعاء مخطّط تنفيذ ولا تنظيم ولا ختم مهني',
    dcj['construction_drawing_claimed'] is False
    and dcj['regulatory_claimed'] is False
    and dcj['professional_stamp_claimed'] is False
    and dcj['cad_interoperability_claimed'] is False)
chk('S-D10 لا كلفة ولا جدول كمّيات تعاقدي',
    dcj['boq_claimed'] is False and dcj['cost_estimation_supported'] is False
    and 'cost' in ' '.join(dcj['forbidden_quantity_fields']))
chk('S-D11 كل حدّ معلَن ومنتهٍ وموجب',
    all(isinstance(v, (int, float)) and 0 < v < float('inf')
        for v in dcj['limits'].values()))
chk('S-D12 قائمتا سماح للمعرّفات وأسماء الملفّات معلَنتان',
    isinstance(dcj['safe_id_pattern'], str) and dcj['safe_id_pattern']
    and isinstance(dcj['safe_filename_pattern'], str))
chk('S-D13 مفاتيح النموذج الأوّلي مرفوضة مفاتيحَ خاصّية',
    all(k in dcj['forbidden_property_keys']
        for k in ('__proto__', 'constructor', 'prototype')))
chk('S-D14 لوحة التوثيق لا تعرض أي أداة تعديل هندسي',
    all(c in dcj['panel_forbidden_controls']
        for c in ('MOVE_WALL', 'MOVE_DOOR', 'RESIZE_SPACE', 'DELETE_SPACE',
                  'ADD_WALL', 'EDIT_MODEL', 'AUTO_FIX_CLASH',
                  'AUTO_ROUTE_MEP', 'APPROVE_DRAWING')))
chk('S-D15 لا مفتاح ولا سرّ في مواصفة التوثيق',
    not any(re.search(r'api[_-]?key|secret|token|password|credential', k, re.I)
            for k in _walk_keys(dcj)))
chk('S-D16 لا خروج من مجلّد التصدير',
    dcj['export_directory_escape_allowed'] is False)
chk('S-D17 لا إعادة توليد تلقائية ولا كتابة فوق التاريخ',
    dcj['auto_regenerate'] is False
    and dcj['history_overwrite_allowed'] is False)
chk('S-D18 الحالات المقيَّدة معلَنة ولا يضعها النظام',
    'APPROVED_FOR_CONSTRUCTION' in dcj['restricted_statuses']
    and 'explicit authorised user action' in dcj['restricted_status_note'])
chk('S-D19 اتّجاه الواجهة لا يعكس الهندسة',
    dcj['rtl_affects_geometry'] is False)
chk('S-D20 لا صور ذكاء اصطناعي في الرسم التقني',
    dcj['technical_drawing_ai_content_allowed'] is False)
chk('S-D21 حدود التوقّف معلَنة وتشمل التصميم والكلفة والاعتماد',
    all(b in dcj['hard_stop_boundaries']
        for b in ('STRUCTURAL_DESIGN', 'MEP_DESIGN', 'COST_ESTIMATION',
                  'PROFESSIONAL_APPROVAL', 'AUTONOMOUS_DESIGN')))

# حمولات توثيق مشوّهة حقيقية تمرّ في الوحدة نفسها — لا نمذجة
_DPRJ = None
try:
    import acs_authoring as _AU2
    import copy as _copy2
    _m = json.loads(_open('tests/phase3/fixtures/base_fixtures.json',
                          encoding='utf-8').read())['villa']
    _DPRJ = _AU2.create_project(_copy2.deepcopy(_m), 'bld_0', 'IMPORT', None)
except Exception as _e:                                           # noqa: BLE001
    chk('S-D22 a documentation project could be built for the adversarial run',
        False, str(_e))
if _DPRJ is not None:
    _DSRC = _D.sources(_DPRJ)
    _DH = _DPRJ['model_hash']
    _MAL = [
        ('not a dict', 'x'),
        ('unknown view type', {'view_type': 'NOPE'}),
        ('unsupported view type', {'view_type': 'THREE_D_REFERENCE'}),
        ('unknown level', {'view_type': 'FLOOR_PLAN', 'level_id': 'nope'}),
        ('unknown scale', {'view_type': 'FLOOR_PLAN', 'scale': '1:7'}),
        ('unknown paper implied', {'view_type': 'FLOOR_PLAN', 'scale': 3}),
        ('non-finite cut', {'view_type': 'SECTION',
                            'cut_plane': {'axis': 'x', 'at': float('nan')}}),
        ('infinite cut', {'view_type': 'SECTION',
                          'cut_plane': {'axis': 'x', 'at': float('inf')}}),
        ('out of bounds cut', {'view_type': 'SECTION',
                               'cut_plane': {'axis': 'x', 'at': 1e12}}),
        ('bad axis', {'view_type': 'SECTION',
                      'cut_plane': {'axis': 'y', 'at': 1}}),
        ('malformed crop', {'view_type': 'FLOOR_PLAN', 'crop_region': [1, 2]}),
        ('non-finite crop', {'view_type': 'FLOOR_PLAN',
                             'crop_region': [0, 0, float('inf'), 1]}),
        ('unknown discipline', {'view_type': 'FLOOR_PLAN',
                                'discipline': 'ASTROLOGY'}),
    ]
    for _n, _spec in _MAL:
        try:
            _r = _D.view_definition(_DPRJ, _spec, _DSRC['arch'])
            _crashed = False
        except Exception:                                         # noqa: BLE001
            _r, _crashed = None, True
        chk('S-D23 %s does not crash the documentation layer' % _n,
            _crashed is False)
        if not _crashed:
            chk('S-D24 %s is refused with a typed issue' % _n,
                _r['valid'] is False and bool(_r['issues']))
            chk('S-D25 %s reports only declared issue codes' % _n,
                all(i['code'] in dcj['issue_codes'] for i in _r['issues']))
    chk('S-D26 لا حمولة مشوّهة غيّرت النموذج', _DPRJ['model_hash'] == _DH)
    for _bad in ('B7', None, 3, 'A3 '):
        _sh = _D.compose_sheet(_DPRJ, {'paper_size': _bad, 'viewports': []}, {})
        chk('S-D27 paper size %r is refused' % _bad, _sh['valid'] is False)
    for _fn in ('../a.svg', '/etc/passwd', '..\\a.svg', 'a/b.svg', 'CON',
                'x' * 300):
        chk('S-D28 filename %r is refused' % _fn[:14],
            _D.safe_filename(_fn) is None)
    chk('S-D29 لا مفتاح كائن من نصّ خارجي',
        all(_D.safe_key(k) is False for k in dcj['forbidden_property_keys']))

# -------------------------------------------------------------- المرحلة 9.1
import acs_pbr as _PQ                                             # noqa: E402
pq = _open('acs_pbr.py', encoding='utf-8').read()
pqj = json.loads(_open('acs_pbr.json', encoding='utf-8').read())
QB = '/* ===== ACS PBR QUALITY (generated by tools/build_pbr_browser.py) ===== */'
QE = '/* ===== END ACS PBR QUALITY ===== */'
chk('S-Q1 طبقة الجودة بايثون بلا تنفيذ ديناميكي', no_exec(pq))
chk('S-Q2 كتلة الجودة المولَّدة موجودة مرّة واحدة بالضبط',
    idx.count(QB) == 1 and idx.count(QE) == 1)
pqblock = idx[idx.index(QB):idx.index(QE)]
chk('S-Q3 نسخة المتصفّح من طبقة الجودة بلا eval/new Function', no_exec(pqblock))
chk('S-Q4 فحص التنفيذ الديناميكي غير عقيم على كتلة الجودة',
    not no_exec(pqblock + '\nvar x = eval("1+1");'))
chk('S-Q5 الطبقة عرضية فقط ولا تكتب إلى النموذج',
    pqj['presentation_only'] is True and pqj['writes_to_model'] is False
    and pqj['mutates_engineering_model'] is False
    and pqj['reverse_write_allowed'] is False)
chk('S-Q6 بصمة النموذج من النموذج وحده وبصمة العرض من الإعداد وحده',
    pqj['model_hash_inputs'] == ['model']
    and pqj['presentation_config_hash_inputs'] == ['config'])
chk('S-Q7 لا ترقية خامة عرضية إلى خاصّية هندسية',
    pqj['engineering_material_promotion_allowed'] is False
    and all(b in pqj['hard_stop_boundaries']
            for b in ('PRESENTATION_TO_ENGINEERING_PROMOTION',
                      'AI_CANONICAL_GEOMETRY_MUTATION', 'RUNTIME_CDN_FETCH')))
chk('S-Q8 لا CDN وقت التشغيل في كتلة الجودة ولا في الجسر',
    'http://' not in pqblock and 'https://' not in pqblock
    and "import('http" not in idx and 'import("http' not in idx)
chk('S-Q9 نسيج بعيد مرفوض وقائمة المخطّطات فارغة',
    pqj['texture_policy']['remote_texture_allowed'] is False
    and pqj['texture_policy']['allowed_schemes'] == []
    and pqj['remote_environment_allowed'] is False)
chk('S-Q10 كل مسار نسيج معادٍ يُرفض',
    all(not _PQ.texture_path_ok(x)['ok'] for x in
        ['https://cdn.evil/x.png', '//evil/x.png', '../secret.png',
         'assets/materials/../../.env', '/etc/passwd',
         'assets/materials/x.svg', 'assets/materials/' + 'a' * 200 + '.png',
         'javascript:alert(1)', '']))
chk('S-Q11 لا ادّعاء واقعية مصوَّرة ولا عرض خارجي',
    pqj['photorealism_claimed'] is False
    and pqj['offline_render_claimed'] is False
    and pqj['path_tracing_claimed'] is False)
chk('S-Q12 أضواء MEP لا يُعاد استعمالها أضواء عرض',
    pqj['mep_lights_reused_as_presentation'] is False)
chk('S-Q13 ULTRA لا يُختار تلقائياً',
    pqj['auto_max_profile'] != 'ULTRA'
    and _PQ.auto_profile({'webgl2': True, 'max_texture_size': 99999})
    ['ultra_auto_selected'] is False)
chk('S-Q14 مفاتيح النموذج الأوّلي مرفوضة في تجاوزات الخامات',
    all(_PQ.safe_key(k) is False for k in pqj['forbidden_property_keys'])
    and not any(i['code'] not in pqj['issue_codes']
                for i in _PQ.material('plaster',
                                      {'__proto__': 1})['issues']))
chk('S-Q15 لوحة الجودة بلا أي أداة تعديل هندسي',
    all(c in pqj['panel_forbidden_controls']
        for c in ('MOVE_WALL', 'RESIZE_SPACE', 'EDIT_MODEL',
                  'SET_FIRE_RATING', 'SET_MATERIAL_GRADE')))
chk('S-Q16 حدود التعريض والقياس معلَنة ومنتهية',
    0 < pqj['limits']['min_exposure'] < pqj['limits']['max_exposure'] < 10
    and 0 < pqj['limits']['max_pixel_ratio'] <= 4
    and 0 < pqj['limits']['max_capture_px'] <= 8192)
chk('S-Q17 سياق العرض مستبعَد بنيوياً من BIM والتوثيق والكمّيات',
    all(x in pqj['ground_context']['excluded_from']
        for x in ('BIM', 'DOCUMENTATION', 'QUANTITIES', 'MODEL_HASH'))
    and pqj['ground_context']['roads_generated'] is False
    and pqj['ground_context']['neighboring_buildings_generated'] is False)

print('\nBACKEND/CONFIG SECURITY: %d passed, %d failed' % (p[0],f[0]))
sys.exit(1 if f[0] else 0)