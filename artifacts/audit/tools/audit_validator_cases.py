"""Recheck the audit's own counterexamples; not the missing original 22."""
import json
import sys
import time
from pathlib import Path

root, inputs, out = [Path(value).resolve() for value in sys.argv[1:4]]
sys.path.insert(0, str(root))
import acs_validate as V

names = ("valid_control", "closed_room_without_access", "furniture_outside_room",
         "object_outside_room", "negative_dimensions", "nonfinite_position",
         "invalid_opening_edge", "door_above_wall", "window_above_wall",
         "duplicate_room_identity", "stair_vertical_misalignment",
         "elevator_vertical_misalignment")
rows = []
for name in names:
    model = json.loads((inputs / (name + ".json")).read_text())
    start = time.perf_counter()
    try:
        issues, stats = V.validate_building(model)
        rows.append({"case": name, "issues": issues, "stats": stats,
                     "matched_expectation": bool(issues) == (name != "valid_control"),
                     "seconds": time.perf_counter() - start})
    except Exception as error:
        rows.append({"case": name, "exception_type": type(error).__name__,
                     "matched_expectation": False, "seconds": time.perf_counter() - start})
result = {"scope": "11 audit counterexamples individually plus one valid control; NOT the original independent 22-issue fixture",
          "matched": sum(row["matched_expectation"] for row in rows), "cases": rows}
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print({"matched": result["matched"], "cases": len(rows), "original_22": "NOT_VERIFIED"})
sys.exit(0 if result["matched"] == len(rows) else 1)
