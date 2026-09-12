from pathlib import Path
import subprocess

path = Path('tools/acs_plan_handoff.py')
previous = subprocess.check_output(
    ['git', 'show', 'HEAD^1:tools/acs_plan_handoff.py'], text=True
)
start_marker = '\ndef _require_explicit_approved_room_presentation_geometry(building: dict) -> None:\n'
end_marker = '\ndef compile_approved_baseline(\n'
start = previous.index(start_marker)
end = previous.index(end_marker, start)
guard = previous[start:end]

current = path.read_text(encoding='utf-8')
if start_marker not in current:
    insert_at = current.index(end_marker)
    current = current[:insert_at] + guard + current[insert_at:]

call = '    _require_explicit_approved_room_presentation_geometry(building)\n'
if call not in current:
    anchor = '    _require_explicit_warehouse_dock_geometry(building)\n'
    assert anchor in current
    current = current.replace(anchor, anchor + call, 1)

path.write_text(current, encoding='utf-8')
