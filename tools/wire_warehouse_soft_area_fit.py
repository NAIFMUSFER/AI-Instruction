#!/usr/bin/env python3
# trigger after workflow installation
from pathlib import Path

def patch(path,old,new):
 p=Path(path); s=p.read_text()
 if new in s:return
 if s.count(old)!=1: raise SystemExit(f'{path}: anchor={s.count(old)}')
 p.write_text(s.replace(old,new,1))

patch('acs_workspace_service.py',"""            if warehouse and target is not None:\n                from warehouse_program_feasibility import generated_indoor_area\n                generated=generated_indoor_area(result['building'])\n                if generated is not None and generated > target + 1e-8*max(1,target):\n                    raise PlanError('WAREHOUSE_PROGRAM_EXCEEDS_BUILDING_TARGET',\n                                    'Generated indoor warehouse program exceeds the confirmed building target')\n            from acs_plan_overlap_repair import repair_overlap\n            result[\"building\"] = repair_overlap(result[\"building\"], prompt, budget)""",
"""            if warehouse and target is not None:\n                from warehouse_program_feasibility import generated_indoor_area\n                from warehouse_soft_area_fit import fit_soft_area\n                generated=generated_indoor_area(result['building'])\n                if generated is not None and generated > target + 1e-8*max(1,target):\n                    # Provider room rectangles are proposals, not hard requirements.\n                    # Fit only their soft area budget deterministically; confirmed\n                    # role minima remain hard and fail structured when infeasible.\n                    result['building'] = fit_soft_area(result['building'], requirements, target)\n            from acs_plan_overlap_repair import repair_overlap\n            result[\"building\"] = repair_overlap(result[\"building\"], prompt, budget)""")
patch('Dockerfile','COPY warehouse_program_feasibility.py ./\n','COPY warehouse_program_feasibility.py ./\nCOPY warehouse_soft_area_fit.py ./\n')
print('wired #161')
