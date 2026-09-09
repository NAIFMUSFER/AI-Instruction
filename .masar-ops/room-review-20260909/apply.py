"""Integrate the proposed inspector only into the exact inspected application baseline."""
from pathlib import Path
import hashlib, json, subprocess
ROOT=Path('masar-studio');STAGED=Path('.masar-ops/room-review-20260909')
expected_blobs={
 'src/plan-inspection.js':'2b17e56e0a8b61201ca89e795e60fc9ab7b029fd',
 'tools/build.mjs':'49c7b709cc4948992239812fb71d0e163acf2ba2',
 'public/sw.js':'9f7b1f1d8f969edce6c6220191ff3b49d5f88f33',
 'tests/browser_http.py':'c149e04cd1aac0df8248e115d44b1c3323c9ecff'
}
for name,sha in expected_blobs.items():
    actual=subprocess.check_output(['git','hash-object',str(ROOT/name)],text=True).strip()
    assert actual==sha,'Baseline changed: '+name
assert hashlib.sha256((ROOT/'src/style.css').read_bytes()).hexdigest()=='07cbd0bb1305eefab54f5c9b07a554402215f10944876dc1c2c9b4ff8231359e'
def replace(path,old,new):
    p=ROOT/path;s=p.read_text();assert s.count(old)==1,(path,old,s.count(old));p.write_text(s.replace(old,new))
for filename,dst in [('room-review.js','src/room-review.js'),('room-review.test.mjs','tests/room-review.test.mjs'),('room_review_browser.py','tests/room_review_browser.py')]:
    assert not (ROOT/dst).exists(),dst
    (ROOT/dst).write_bytes((STAGED/filename).read_bytes())
replace('src/plan-inspection.js',"import { clone, assertModel }", "import { attachRoomReview } from './room-review.js';\nimport { clone, assertModel }")
replace('src/plan-inspection.js','    const level = snapshot.levels.find','    let level = snapshot.levels.find')
replace('src/plan-inspection.js','    const svgText = planSVG','    let svgText = planSVG')
replace('src/plan-inspection.js','${E(snapshot.title)} · ${E(level.name)} · ${E(revisionLabel)}','${E(snapshot.title)} · <span data-inspection-level>${E(level.name)}</span> · ${E(revisionLabel)}')
replace('src/plan-inspection.js','    <h3>عناصر الموقع الخارجي</h3>','    <div id="plan-room-review"></div>\n    <h3>عناصر الموقع الخارجي</h3>')
replace('src/plan-inspection.js',", svg = frame.querySelector('svg'), output = root.querySelector('#plan-inspection-scale');",", output = root.querySelector('#plan-inspection-scale');\n    let svg = frame.querySelector('svg');")
anchor="    root.querySelectorAll('[data-plan-feature]').forEach(button => button.addEventListener('click', () => {"
insert="""    root.dataset.levelId=level.id;
    const showLevel = id => {
        const next=snapshot.levels.find(l=>l.id===id);if(!next)return;
        level=next;svgText=planSVG(snapshot,level.id,{interactive:false,dimensions:true,furniture:true});
        frame.innerHTML=svgText;svg=frame.querySelector('svg');pointers.clear();
        root.dataset.levelId=level.id;root.querySelector('[data-inspection-level]').textContent=level.name;
        view=fitPlanView(snapshot.site.width,snapshot.site.depth);paint();
    };
    attachRoomReview({ root:root.querySelector('#plan-room-review'),model:snapshot,levelId:level.id,revisionLabel,showLevel,download,
        focusRoom:(id,floorId)=>{
            if(level.id!==floorId)showLevel(floorId);
            const index=level.rooms.findIndex(r=>r.id===id),room=level.rooms[index];if(!room)return;
            const z=Math.max(1,Math.min(6,(snapshot.site.width+5)/(room.w*1.7),(snapshot.site.depth+5)/(room.d*1.7)));
            view=fitPlanView(snapshot.site.width,snapshot.site.depth);move({zoom:z});
            move({dx:room.x+room.w/2-(view.x+view.w/2),dy:snapshot.site.depth-room.y-room.d/2-(view.y+view.d/2)});
            svg.querySelectorAll('g.room').forEach((group,i)=>group.classList.toggle('inspection-room-selected',i===index));
            frame.focus({preventScroll:true});frame.scrollIntoView({block:'nearest'});
        }
    });
"""
replace('src/plan-inspection.js',anchor,insert+anchor)
replace('tools/build.mjs',"'src/plan-inspection.js'","'src/room-review.js','src/plan-inspection.js'")
replace('public/sw.js',"masar-4.1.0-shell-v7-plan-inspection","masar-4.1.0-shell-v8-room-review")
replace('public/sw.js',"'/src/plan-inspection.js'","'/src/room-review.js','/src/plan-inspection.js'")
replace('tests/browser_http.py',"'/src/plan-inspection.js'","'/src/room-review.js', '/src/plan-inspection.js'")
css='''
/* Read-only room review: controls reflow instead of clipping native inputs. */
#plan-room-review{min-width:0;margin-block:1.2rem}
.room-review-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.room-review-fields .field,.room-review-fields input,.room-review-fields select{min-width:0;width:100%;max-width:100%;box-sizing:border-box}
.room-review-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;max-height:260px;overflow:auto;overscroll-behavior:contain;padding:4px}
.room-review-row{display:flex;flex-direction:column;align-items:flex-start;gap:4px;min-width:0;min-height:48px;width:100%;padding:10px 12px;border:1px solid #d9dfd5;border-radius:9px;background:#fff;text-align:start;font:inherit;color:inherit;overflow-wrap:anywhere;cursor:pointer}
.room-review-row[aria-pressed="true"]{border-color:#285b4b;background:#e4f0e8}
.room-review-row:focus-visible{outline:3px solid #285b4b;outline-offset:1px}
.room-review-row span{font-size:.86rem}
#room-review-count{display:block;margin-block:8px}
#room-review-detail{overflow-wrap:anywhere;margin-block:12px}
#room-review-detail h4{margin-block:0 8px}
.room-review-downloads{display:flex;flex-wrap:wrap;gap:8px;margin-block:12px}
.room-review-downloads .btn{white-space:normal;max-width:100%}
#plan-inspection-frame .inspection-room-selected>rect:first-child,#plan-inspection-frame .inspection-room-selected>polygon:first-child{stroke:#125d45;stroke-width:.18;stroke-dasharray:.2 .1;fill:#a9d6c4}
@media(max-width:560px){.room-review-fields,.room-review-list{grid-template-columns:minmax(0,1fr)}}
'''
p=ROOT/'src/style.css';p.write_text(p.read_text()+css)
for name in ['room_review_browser.py']:
    compile((ROOT/'tests'/name).read_text(),name,'exec')
paths=list(expected_blobs)+['src/style.css','src/room-review.js','tests/room-review.test.mjs','tests/room_review_browser.py']
out=ROOT/'test-output/room-review';out.mkdir(parents=True,exist_ok=True)
(out/'source-hashes.json').write_text(json.dumps({name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in paths},indent=2))
print('Applied guarded room review; source is uncommitted until all gates pass.')
