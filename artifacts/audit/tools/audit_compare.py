"""Compare every saved export byte-for-byte; never labels unequal output a pass."""
import hashlib
import json
import sys
from pathlib import Path

before, after, output = [Path(p).resolve() for p in sys.argv[1:4]]
rows = []
for case in ("warehouse", "chalet"):
    left, right = before / case, after / case
    files = []
    names = sorted({p.name for p in left.iterdir()} | {p.name for p in right.iterdir()})
    for name in names:
        a, b = left / name, right / name
        aa, bb = a.read_bytes() if a.is_file() else None, b.read_bytes() if b.is_file() else None
        files.append({"file": name, "equal_bytes": aa is not None and aa == bb,
                      "before_sha256": hashlib.sha256(aa).hexdigest() if aa is not None else None,
                      "after_sha256": hashlib.sha256(bb).hexdigest() if bb is not None else None})
    rows.append({"case": case, "files": files})
output.write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps({r["case"]: all(f["equal_bytes"] for f in r["files"]) for r in rows}))
