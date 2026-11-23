"""Embed the approved public fixtures' room boundaries for offline classic-script boot."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "docs/delivery/2026-11-10/fixtures"
TARGET = ROOT / "public/app/boot/engine-guard.js"
START = "  /* BEGIN GENERATED GUEST PLANS */"
END = "  /* END GENERATED GUEST PLANS */"


def generate():
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    result = {}
    for key in ("villa", "warehouse"):
        model = json.loads((FIXTURES / f"{key}.json").read_text())
        receipt = next(row for row in manifest if row["fixture"] == key)
        result[key] = {
            "revision": receipt["revision_id"], "hash": receipt["model_hash"],
            "levels": model["levels"],
            "rooms": {template: [{field: room[field] for field in ("rect", "name", "id")}
                                 for room in floor["rooms"]]
                      for template, floor in model["floors"].items()},
        }
    current = TARGET.read_text()
    before, body = current.split(START, 1)
    _, after = body.split(END, 1)
    payload = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return before + START + "\n  var guestPlans = " + payload + ";\n" + END + after


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    updated = generate()
    if args.check:
        if updated != TARGET.read_text():
            raise SystemExit("Guest schematic payload differs from its public fixture receipts")
    else:
        TARGET.write_text(updated)
