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


def generate(landscape=False, previews=False):
    model = json.loads(node("""
        import {apartmentSample} from './public/app/core/local-apartment.mjs';
        console.log(JSON.stringify(apartmentSample()));
    """))
    arch = compile_architecture(model)
    drawings = {}
    for level in model["levels"]:
        index = level["index"]
        packet = floor_plan(arch, index)
        rendered = json.loads(node("""
            import {readFileSync} from 'node:fs';
            import {renderGuestFloorSVG} from './public/app/ui/guest-floor-plan.mjs';
            const {packet, model, landscape, previews} = JSON.parse(readFileSync(0, 'utf8'));
            const sheet = renderGuestFloorSVG(packet, model, {landscape});
            const preview = previews ? renderGuestFloorSVG(packet, model, {schedule:false}) : null;
            console.log(JSON.stringify({sheet, preview}));
        """, json.dumps({"packet": packet, "model": model, "landscape": landscape, "previews": previews}, ensure_ascii=False)))
        drawings[f"apartment-floor-{index}.svg"] = rendered["sheet"] + "\n"
        if previews:
            drawings[f"apartment-floor-{index}-preview.svg"] = rendered["preview"] + "\n"
    return drawings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "public/guest-plans"
    drawings = generate(previews=True)
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
    sheets = sum(not name.endswith("-preview.svg") for name in drawings)
    previews = len(drawings) - sheets
    action = "Verified" if args.check else "Generated"
    print(f"{action} {sheets} apartment floor sheets and {previews} inline previews")
