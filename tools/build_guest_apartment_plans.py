"""Build the named public apartment's offline drawings with the actual plan projector."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from acs_arch import compile_architecture
from acs_visual import floor_plan


def node(script, payload=None):
    return subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=ROOT, input=payload, text=True, capture_output=True, check=True,
    ).stdout


def generate(landscape=False):
    model = json.loads(node("""
        import {apartmentSample} from './public/app/core/local-apartment.mjs';
        console.log(JSON.stringify(apartmentSample()));
    """))
    arch = compile_architecture(model)
    drawings = {}
    for level in model["levels"]:
        index = level["index"]
        packet = floor_plan(arch, index)
        svg = node("""
            import {readFileSync} from 'node:fs';
            import {renderGuestFloorSVG} from './public/app/ui/guest-floor-plan.mjs';
            const {packet, model, landscape} = JSON.parse(readFileSync(0, 'utf8'));
            console.log(renderGuestFloorSVG(packet, model, {landscape}));
        """, json.dumps({"packet": packet, "model": model, "landscape": landscape}, ensure_ascii=False))
        drawings[f"apartment-floor-{index}.svg"] = svg
    return drawings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "public/guest-plans"
    drawings = generate()
    if args.check:
        if set(drawings) != {p.name for p in target.glob("apartment-floor-*.svg")}:
            raise SystemExit("Wrong set of public apartment floor drawings")
        for name, svg in drawings.items():
            if (target / name).read_text(encoding="utf-8") != svg:
                raise SystemExit(f"Stale guest apartment drawing: {name}")
    else:
        target.mkdir(parents=True, exist_ok=True)
        for name, svg in drawings.items():
            (target / name).write_text(svg, encoding="utf-8")
    print(f"Verified {len(drawings)} exact apartment floor plans" if args.check else
          f"Generated {len(drawings)} exact apartment floor plans")
