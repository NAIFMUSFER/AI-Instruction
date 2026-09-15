#!/usr/bin/env python3
"""One-shot exact patch for #157; fail closed on source drift. Triggered after workflow installation."""
from pathlib import Path

p = Path("acs_plan_chunks.py")
text = p.read_text(encoding="utf-8")
old = '''    site = (envelope or {}).get("site") or {}\n    by_template = {}\n    unresolved = []\n    for i, z in enumerate(outline_zones):\n        zid = z["id"]\n        tmpl = z.get("template") or "t"\n        room = resolved.get(zid)\n'''
new = '''    site = (envelope or {}).get("site") or {}\n    # A single explicit level is authoritative for floor-template identity.\n    # Outline zones may use the provider/default template token (often ``t``);\n    # binding that token to the sole declared level does not change geometry or\n    # room identity. Multi-level mismatches remain ambiguous and fail closed.\n    declared_levels = (envelope or {}).get("levels") if isinstance(envelope, dict) else None\n    sole_template = None\n    if (isinstance(declared_levels, list) and len(declared_levels) == 1\n            and isinstance(declared_levels[0], dict)\n            and isinstance(declared_levels[0].get("template"), str)\n            and declared_levels[0]["template"].strip()):\n        sole_template = declared_levels[0]["template"]\n    rebound_from = set()\n    by_template = {}\n    unresolved = []\n    for i, z in enumerate(outline_zones):\n        zid = z["id"]\n        source_tmpl = z.get("template") or "t"\n        tmpl = sole_template or source_tmpl\n        if sole_template and source_tmpl != sole_template:\n            rebound_from.add(source_tmpl)\n        room = resolved.get(zid)\n'''
if new not in text:
    if text.count(old) != 1:
        raise SystemExit(f"first anchor count={text.count(old)}")
    text = text.replace(old, new, 1)
old2 = '''    if unresolved:\n        issues.append({"code": "PLAN_ZONE_UNRESOLVED",\n                       "count": len(unresolved), "ids": unresolved[:32]})\n\n    building = {}\n'''
new2 = '''    if unresolved:\n        issues.append({"code": "PLAN_ZONE_UNRESOLVED",\n                       "count": len(unresolved), "ids": unresolved[:32]})\n    if rebound_from:\n        issues.append({"code": "PLAN_SINGLE_LEVEL_TEMPLATE_REBOUND",\n                       "from": sorted(rebound_from), "to": sole_template})\n\n    building = {}\n'''
if new2 not in text:
    if text.count(old2) != 1:
        raise SystemExit(f"second anchor count={text.count(old2)}")
    text = text.replace(old2, new2, 1)
old3 = '''    # ترتيب القوالب من البيان لا من قاموس: نفس المدخل ⇒ نفس المخرج دائماً.\n    tmpl_order = []\n    for z in outline_zones:\n        t = z.get("template") or "t"\n        if t not in tmpl_order:\n            tmpl_order.append(t)\n    building["floors"] = {t: {"rooms": by_template.get(t, [])}\n                          for t in tmpl_order}\n'''
new3 = '''    # ``by_template`` is populated in outline order, so key order remains\n    # deterministic while reflecting the single-level binding above.\n    tmpl_order = list(by_template)\n    building["floors"] = {t: {"rooms": by_template.get(t, [])}\n                          for t in tmpl_order}\n'''
if new3 not in text:
    if text.count(old3) != 1:
        raise SystemExit(f"third anchor count={text.count(old3)}")
    text = text.replace(old3, new3, 1)
p.write_text(text, encoding="utf-8")
print("#157 single-level template binding applied")
