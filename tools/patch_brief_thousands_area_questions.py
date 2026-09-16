#!/usr/bin/env python3
from pathlib import Path

core = Path('public/app/core/brief-program.mjs')
s = core.read_text()
old = """    if(ambiguous.test(text)&&!areaPattern.test(text)){\n      if(/[0-9]/.test(text))questions.push('راجع الشرط أو نطاق العدد في: «'+chunk[0].trim().slice(0,200)+'». أضف القيم الإجمالية المؤكدة في الحقول.');\n      continue;\n    }\n"""
new = """    // A comma-grouped measured area such as 5,000 m² is an ordinary\n    // thousands separator, not a numeric range/decimal ambiguity. It may stay\n    // in the brief without creating a noisy pre-generation question. We do\n    // not promote it to a hard requirement unless a supported area phrase\n    // matched above; confirmed form values remain the source of truth.\n    const groupedMeasuredArea=/[0-9]+(?:[,٬][0-9]{3})+\\s*(?:م(?:تر)?\\s*(?:مربع|²)|m²|sqm)(?![\\p{L}\\p{N}])/iu;\n    if(ambiguous.test(text)&&!areaPattern.test(text)&&!groupedMeasuredArea.test(text)){\n      if(/[0-9]/.test(text))questions.push('راجع الشرط أو نطاق العدد في: «'+chunk[0].trim().slice(0,200)+'». أضف القيم الإجمالية المؤكدة في الحقول.');\n      continue;\n    }\n"""
if s.count(old) != 1:
    raise SystemExit(f'core anchor count={s.count(old)}')
core.write_text(s.replace(old, new, 1))

test = Path('tests/remediation/test_brief_program.mjs')
t = test.read_text()
anchor = """  ['Conflicting description and inputs stop before generation', () => {\n"""
case = """  ['Thousands-grouped measured areas do not create fake ambiguity questions', () => {\n    const text='أريد مستودعًا بمساحة بناء إجمالية تقارب 5,000 م²، ثم Zoning Plan يوزع المساحة الإجمالية 5,000 م²، ولا تفترض أن مساحة الأرض نفسها 5,000 م².';\n    const a=analyzeBrief(text);\n    assert.equal(a.questions.length,0,'5,000 m² is a measured area with a thousands separator, not a range');\n    assert.equal(a.candidates.length,0,'unsupported area wording must remain prose rather than become an invented hard requirement');\n    assert.ok(analyzeBrief('1,000 bedrooms').questions.length,'non-area grouped counts remain reviewable instead of silently becoming totals');\n  }],\n"""
if case in t:
    raise SystemExit('test already patched')
if t.count(anchor) != 1:
    raise SystemExit(f'test anchor count={t.count(anchor)}')
test.write_text(t.replace(anchor, case + anchor, 1))
print('patched brief grouped measured-area question handling + regression')
