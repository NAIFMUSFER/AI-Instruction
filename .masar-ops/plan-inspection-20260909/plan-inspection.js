/** Read-only plan navigation. All geometry and downloads use a captured model.
 * Camera gestures never call the author's move/resize/history/persistence paths.
 */
import { clone, assertModel } from '../shared/model.js';
import { planSVG, escapeHTML } from '../shared/geometry.js';
const limit = (n, lo, hi) => Math.min(hi, Math.max(lo, n));
export function fitPlanView(width, depth) {
    if (![width, depth].every(n => Number.isFinite(n) && n > 0)) throw Error('أبعاد عرض المخطط غير صالحة.');
    return { siteWidth: width, siteDepth: depth, x: -2.5, y: -2.5, w: width + 5, d: depth + 5, zoom: 1 };
}
export function navigatePlanView(view, { zoom = view.zoom, dx = 0, dy = 0, anchorX = .5, anchorY = .5 } = {}) {
    if (![view.siteWidth, view.siteDepth, view.x, view.y, view.w, view.d, zoom, dx, dy, anchorX, anchorY].every(Number.isFinite)) throw Error('حركة عرض غير صالحة.');
    const base = fitPlanView(view.siteWidth, view.siteDepth), z = limit(zoom, 1, 6), w = base.w / z, d = base.d / z;
    const ax = limit(anchorX, 0, 1), ay = limit(anchorY, 0, 1);
    return { ...base, zoom: z, w, d,
        x: limit(view.x + (view.w - w) * ax + dx, base.x, base.x + base.w - w),
        y: limit(view.y + (view.d - d) * ay + dy, base.y, base.y + base.d - d) };
}
export function openPlanInspection({ model, levelId, revisionLabel, showModal, download }) {
    const snapshot = clone(assertModel(model));
    const level = snapshot.levels.find(l => l.id === levelId) || snapshot.levels[0];
    const features = snapshot.site.features || [], E = escapeHTML, num = n => Number(n).toLocaleString('en-US', { maximumFractionDigits: 2 });
    const svgText = planSVG(snapshot, level.id, { interactive: false, dimensions: true, furniture: true });
    showModal('فحص المخطط والموقع', `<section id="plan-inspection" data-model-id="${E(snapshot.id)}"><p class="modal-lead">${E(snapshot.title)} · ${E(level.name)} · ${E(revisionLabel)}<br>عرض للقراءة فقط؛ التكبير والسحب لا ينقلان الغرف ولا ينشئان نسخة.</p>
    <div class="plan-inspection-controls" role="group" aria-label="تنقل المخطط للقراءة فقط"><button type="button" class="btn light" data-plan-nav="in" aria-label="تكبير المخطط">+</button><output id="plan-inspection-scale" aria-live="polite">100%</output><button type="button" class="btn light" data-plan-nav="out" aria-label="تصغير المخطط">−</button><button type="button" class="btn light" data-plan-nav="fit">إظهار الأرض كاملة</button></div>
    <p class="plan-inspection-hint" id="plan-inspection-help">اسحب المخطط أو قرّب بإصبعين داخل الإطار. لوحة المفاتيح: الأسهم للتحريك، + و− للتكبير، و0 لإظهار الأرض.</p>
    <div id="plan-inspection-frame" tabindex="0" role="region" aria-label="مخطط قابل للتكبير للقراءة فقط" aria-describedby="plan-inspection-help">${svgText}</div>
    <h3>عناصر الموقع الخارجي</h3><p>الأبعاد من مواضع النموذج المفاهيمي، وليست مخططات تنفيذ. اضغط اسم العنصر للوصول إلى موضعه.</p>
    <div class="plan-site-list">${features.length ? features.map((f,i)=>`<button class="plan-site-item" type="button" data-plan-feature="${i}"><strong>${E(f.name)}</strong><span dir="ltr">${num(f.w)} × ${num(f.d)} m · ${num(f.w*f.d)} m²</span></button>`).join('') : '<p class="notice">لا توجد عناصر موقع ممثلة في هذا المشروع؛ الفراغ الخارجي لا يعني وجود حديقة مصممة.</p>'}</div>
    <div class="notice warn">مساحة كل عنصر هي مستطيله المفاهيمي؛ قد تتداخل تخصيصات الموقع، فلا تجمعها باعتبارها مساحات أرض مستقلة. أما أبعاد الغرفة غير المستطيلة فهي أبعاد صندوقها المحيط، وليست مستطيلًا صالحًا للأثاث. لا يوجد اعتماد إنشائي أو تنظيمي.</div>
    <div class="modal-footer"><button class="btn light" type="button" data-plan-save>تنزيل المخطط الكامل SVG</button><button class="btn primary" type="button" data-action="close-modal">العودة للتصميم</button></div></section>`, 'READ-ONLY PLAN / METRES');
    const root = document.querySelector('#plan-inspection'), frame = root.querySelector('#plan-inspection-frame'), svg = frame.querySelector('svg'), output = root.querySelector('#plan-inspection-scale');
    let view = fitPlanView(snapshot.site.width, snapshot.site.depth);
    const pointers = new Map();
    function paint() {
        svg.setAttribute('viewBox', `${view.x} ${view.y} ${view.w} ${view.d}`);
        frame.dataset.zoom = String(view.zoom); output.textContent = `${Math.round(view.zoom * 100)}%`;
        root.querySelector('[data-plan-nav="in"]').disabled = view.zoom >= 6;
        root.querySelector('[data-plan-nav="out"]').disabled = view.zoom <= 1;
    }
    function move(options) { view = navigatePlanView(view, options); paint(); }
    function anchor(clientX, clientY) {
        const matrix = svg.getScreenCTM(); if (!matrix) return { anchorX:.5, anchorY:.5 };
        const pt = svg.createSVGPoint(); pt.x=clientX;pt.y=clientY;const p=pt.matrixTransform(matrix.inverse());
        return { anchorX:(p.x-view.x)/view.w, anchorY:(p.y-view.y)/view.d };
    }
    root.querySelectorAll('[data-plan-nav]').forEach(button => button.addEventListener('click', () => {
        const op=button.dataset.planNav;
        if(op==='fit') { view=fitPlanView(snapshot.site.width,snapshot.site.depth);paint(); }
        else move({zoom:view.zoom*(op==='in'?1.4:1/1.4)});
    }));
    root.querySelectorAll('[data-plan-feature]').forEach(button => button.addEventListener('click', () => {
        const feature=features[Number(button.dataset.planFeature)], z=Math.min(6,Math.max(2,(snapshot.site.width+5)/(feature.w*2)));
        view=fitPlanView(snapshot.site.width,snapshot.site.depth);move({zoom:z});
        move({dx:feature.x+feature.w/2-(view.x+view.w/2),dy:snapshot.site.depth-feature.y-feature.d/2-(view.y+view.d/2)});
        frame.focus({preventScroll:true});frame.scrollIntoView({block:'nearest'});
    }));
    root.querySelector('[data-plan-save]').addEventListener('click', () => download('MASAR-Plan-Inspection.svg',svgText,'image/svg+xml'));
    frame.addEventListener('pointerdown', e => {
        if(e.button!==0)return;
        e.preventDefault();frame.focus({preventScroll:true});pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});frame.setPointerCapture(e.pointerId);
    });
    frame.addEventListener('pointermove', e => {
        if(!pointers.has(e.pointerId))return;
        const old=[...pointers.values()];pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});const next=[...pointers.values()];
        if(next.length===1) {
            const matrix=svg.getScreenCTM();if(matrix)move({dx:-(next[0].x-old[0].x)/matrix.a,dy:-(next[0].y-old[0].y)/matrix.d});
        } else if(next.length===2) {
            const distance=p=>Math.hypot(p[1].x-p[0].x,p[1].y-p[0].y), before=distance(old),after=distance(next);
            if(before>5&&after>5)move({zoom:view.zoom*after/before,...anchor((old[0].x+old[1].x)/2,(old[0].y+old[1].y)/2)});
        }
    });
    for(const event of ['pointerup','pointercancel','lostpointercapture'])frame.addEventListener(event,e=>pointers.delete(e.pointerId));
    frame.addEventListener('keydown', e => {
        const options={ArrowLeft:{dx:-view.w*.15},ArrowRight:{dx:view.w*.15},ArrowUp:{dy:-view.d*.15},ArrowDown:{dy:view.d*.15},'+':{zoom:view.zoom*1.4},'=':{zoom:view.zoom*1.4},'-':{zoom:view.zoom/1.4}};
        if(e.key==='0'){e.preventDefault();view=fitPlanView(snapshot.siteWidth,snapshot.siteDepth);paint();}
        else if(options[e.key]){e.preventDefault();move(options[e.key]);}
    });
    frame.addEventListener('wheel',e=>{if(!e.ctrlKey)return;e.preventDefault();move({zoom:view.zoom*Math.exp(-limit(e.deltaY,-200,200)*.005),...anchor(e.clientX,e.clientY)});},{passive:false});
    paint();
}
