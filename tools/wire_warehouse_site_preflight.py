#!/usr/bin/env python3
from pathlib import Path
p=Path('acs_workspace_service.py'); s=p.read_text()
old="""    residential = U._is_residential(detected)\n    warehouse = detected == 'warehouse'\n    prompt = brief + \"\\n\\nمتطلبات أكدها المستخدم:\\n\" + canonical(requirements)\n"""
new="""    residential = U._is_residential(detected)\n    warehouse = detected == 'warehouse'\n    if warehouse:\n        from warehouse_program_feasibility import warehouse_requirements_preflight\n        preflight = warehouse_requirements_preflight(requirements)\n        if not preflight.get('may_generate_layout', True):\n            if preflight.get('status') == 'BUILDABLE_ENVELOPE_NOT_VERIFIED':\n                raise PlanError(\n                    'WAREHOUSE_BUILDABLE_ENVELOPE_NOT_VERIFIED',\n                    'مساحة المبنى المستهدفة تستهلك كامل مساحة الموقع في مشروع من دور واحد. '
                    'لا يمكن اعتبار كامل الأرض غلافًا بنائيًا متحققًا أو ترك ساحات التشغيل الخارجية دون مساحة. '
                    'أدخل مساحة مبنى أصغر أو موقعًا أكبر؛ لن يخترع ACS ارتدادات أو أبعادًا تنظيمية.'\n                )\n            raise PlanError(\n                'WAREHOUSE_BUILDING_TARGET_INFEASIBLE',\n                'مساحة المبنى المستهدفة لا يمكن احتواؤها حسابيًا ضمن أبعاد الموقع وعدد الأدوار المؤكدة.'\n            )\n    prompt = brief + \"\\n\\nمتطلبات أكدها المستخدم:\\n\" + canonical(requirements)\n"""
if new in s: raise SystemExit('already wired')
if s.count(old)!=1: raise SystemExit(f'anchor count={s.count(old)}')
p.write_text(s.replace(old,new,1))
print('wired warehouse site preflight')
