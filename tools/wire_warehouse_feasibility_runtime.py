#!/usr/bin/env python3
"""One-shot exact wiring for #159. Fails closed if source anchors drift."""
from pathlib import Path


def patch(path, old, new):
    p=Path(path); text=p.read_text(encoding='utf-8')
    if new in text:return
    if text.count(old)!=1: raise SystemExit(f'{path}: anchor count {text.count(old)}')
    p.write_text(text.replace(old,new,1),encoding='utf-8')

patch('public/app/core/brief-program.mjs',
"""  site_width_m:'عرض الموقع (م)', site_depth_m:'عمق الموقع (م)', level_count:'عدد الأدوار',\n  room_count:'عدد فراغات الاستخدام', min_space_area_by_role_m2:'أقل مساحة للاستخدام (م²)',""",
"""  site_width_m:'عرض الموقع (م)', site_depth_m:'عمق الموقع (م)', level_count:'عدد الأدوار',\n  building_target_area_m2:'مساحة المبنى المستهدفة (م²)',\n  room_count:'عدد فراغات الاستخدام', min_space_area_by_role_m2:'أقل مساحة للاستخدام (م²)',""")
patch('public/app/core/brief-program.mjs',
"""    const expected=Number(n)*(unit?factor(unit):1);""",
"""    const numeric=typeof n==='string'?n.replace(/[,٬]/g,''):n;\n    const expected=Number(numeric)*(unit?factor(unit):1);""")
patch('public/app/core/brief-program.mjs',
"""    const text=normal(chunk[0]);\n    if(ambiguous.test(text)){""",
"""    const text=normal(chunk[0]);\n    // Building target area is a planning budget, not site area. Approximate\n    // wording is intentionally reviewable/inferred rather than silently hard.\n    const areaPattern=/(?:مساحة\\s+(?:المبنى|مبنى(?:\\s+المستودع)?)(?:\\s+(?:المستهدفة|المغلقة))?|building\\s+(?:target\\s+)?area)\\s*(?:تقارب|قرابة|حوالي|≈|~)?\\s*[:=]?\\s*(?<n>[0-9]+(?:[,٬][0-9]{3})*(?:\\.[0-9]+)?)\\s*(?:م(?:تر)?\\s*(?:مربع|²)|m²|sqm)(?![\\p{L}\\p{N}])/giu;\n    for(const match of text.matchAll(areaPattern))add('building_target_area_m2',match.groups.n,null,match,chunk.index,'inferred');\n    if(ambiguous.test(text)&&!areaPattern.test(text)){""")
patch('public/app/core/brief-program.mjs',
"""    if(r.metric!=='min_space_area_by_role_m2'&&!r.metric.endsWith('_m')&&!Number.isInteger(r.expected))throw new Error('أدخل عددًا صحيحًا في '+requirementLabel(r)+'.');""",
"""    if(!['min_space_area_by_role_m2','building_target_area_m2'].includes(r.metric)&&!r.metric.endsWith('_m')&&!Number.isInteger(r.expected))throw new Error('أدخل عددًا صحيحًا في '+requirementLabel(r)+'.');""")

patch('acs_workspace_service.py',
"""    residential = U._is_residential(U.detect_type(brief))\n    prompt = brief + \"\\n\\nمتطلبات أكدها المستخدم:\\n\" + canonical(requirements)\n    prompt += \"\\nهدف المقترح \" + option + \": \" + OPTIONS[option]""",
"""    detected = U.detect_type(brief)\n    residential = U._is_residential(detected)\n    warehouse = detected == 'warehouse'\n    prompt = brief + \"\\n\\nمتطلبات أكدها المستخدم:\\n\" + canonical(requirements)\n    prompt += \"\\nهدف المقترح \" + option + \": \" + OPTIONS[option]\n    if warehouse:\n        targets=[r.get('expected') for r in requirements if isinstance(r,dict) and r.get('metric')=='building_target_area_m2']\n        target=targets[0] if len(targets)==1 and type(targets[0]) in (int,float) else None\n        if target is not None:\n            prompt += (\"\\nقيد برنامج المستودع المؤكد: مساحة المبنى الداخلية المستهدفة = \"+str(target)+\" م². \"\n                       \"هذه ليست مساحة الأرض. اجعل مجموع مساحات فراغات floors الداخلية لا يتجاوز هذه الميزانية. \"\n                       \"ساحات الشاحنات والمواقف والدوران الخارجي والتوسع المستقبلي عناصر موقع خارجية وليست غرفًا داخلية. \"\n                       \"لا تخترع setbacks أو أبعاد حريق أو اشتراطات غير معطاة.\")""")
patch('acs_workspace_service.py',
"""        else:\n            from acs_plan_overlap_repair import repair_overlap\n            result[\"building\"] = repair_overlap(result[\"building\"], prompt, budget)""",
"""        else:\n            if warehouse and target is not None:\n                from warehouse_program_feasibility import generated_indoor_area\n                generated=generated_indoor_area(result['building'])\n                if generated is not None and generated > target + 1e-8*max(1,target):\n                    raise PlanError('WAREHOUSE_PROGRAM_EXCEEDS_BUILDING_TARGET',\n                                    'Generated indoor warehouse program exceeds the confirmed building target')\n            from acs_plan_overlap_repair import repair_overlap\n            result[\"building\"] = repair_overlap(result[\"building\"], prompt, budget)""")

patch('warehouse_program_feasibility.py',
"""def warehouse_program_feasibility(*, site_area_m2, building_target_m2, program):""",
"""def generated_indoor_area(building):\n    \"\"\"Measure canonical floor rectangles only; site/outdoor objects are excluded.\"\"\"\n    try:\n        floors=building['floors']\n        if not isinstance(floors,dict): return None\n        total=0.0\n        for floor in floors.values():\n            for room in floor['rooms']:\n                rect=room['rect']\n                if not isinstance(rect,list) or len(rect)!=4: return None\n                w,d=_area(rect[2]),_area(rect[3])\n                if w is None or d is None:return None\n                total += w*d\n        return total\n    except (KeyError,TypeError):\n        return None\n\n\ndef warehouse_program_feasibility(*, site_area_m2, building_target_m2, program):""")

patch('Dockerfile',
"""COPY warehouse_vertical_stage_gate.py ./\n""",
"""COPY warehouse_vertical_stage_gate.py ./\nCOPY warehouse_program_feasibility.py ./\n""")
print('wired #159 runtime feasibility')
