import { authoringDefaults, effectiveAuthoring, openingPoint, sideSpan, windowTypeFor } from './authoring.js';
/** Canonical conceptual geometry. Metres; x=east, y=north, z=up. Never implies code compliance. */
export const VERSION = 1;
export const clone = value => structuredClone(value);
export const round = v => Math.round(v * 1000) / 1000;
export const uid = () => { if (globalThis.crypto.randomUUID)
    return globalThis.crypto.randomUUID(); const a = globalThis.crypto.getRandomValues(new Uint8Array(16)); a[6] = (a[6] & 15) | 64; a[8] = (a[8] & 63) | 128; const h = [...a].map(x => x.toString(16).padStart(2, '0')).join(''); return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`; };
export const KINDS = { living: 'معيشة', majlis: 'مجلس', bedroom: 'غرفة نوم', kitchen: 'مطبخ', bath: 'دورة مياه', stairs: 'درج', elevator: 'مصعد', hall: 'ممر', dining: 'طعام', office: 'مكتب', meeting: 'اجتماعات', reception: 'استقبال', warehouse: 'مستودع', loading: 'استلام وتحميل', retail: 'تجزئة', laundry: 'غسيل', storage: 'تخزين', garage: 'مواقف', service: 'خدمات' };
export const COLORS = { living: '#dfbf94', majlis: '#c3d4c6', bedroom: '#c2cce1', kitchen: '#d4c5b5', bath: '#b5d6db', stairs: '#c9c3b9', elevator: '#b9c2c7', hall: '#e6e1d8', dining: '#dfc6c3', office: '#c8c2da', meeting: '#c9c0d7', reception: '#d9c9ae', warehouse: '#c9cfbf', loading: '#c8d1cc', retail: '#dec9b1', laundry: '#c5d7d7', storage: '#d2d1c2', garage: '#c9c9c4', service: '#ced4c0' };
export function normalizeText(value = '') {
    return String(value).replace(/[٠-٩]/g, c => String('٠١٢٣٤٥٦٧٨٩'.indexOf(c))).replace(/[۰-۹]/g, c => String('۰۱۲۳۴۵۶۷۸۹'.indexOf(c))).replace(/٫/g, '.').replace(/٬/g, '').replace(/[أإآ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').replace(/[ًٌٍَُِّْـ]/g, '').toLowerCase().trim();
}
const wordNumbers = { 'واحد': 1, 'واحده': 1, 'اثنين': 2, 'اثنان': 2, 'اثنتين': 2, 'ثلاث': 3, 'ثلاثه': 3, 'اربع': 4, 'اربعه': 4, 'خمس': 5, 'خمسه': 5, 'ست': 6, 'سته': 6, 'سبع': 7, 'سبعه': 7, 'ثمان': 8, 'ثمانيه': 8, 'تسع': 9, 'تسعه': 9, 'عشر': 10, 'عشره': 10 };
function amount(text, re, fallback) { const m = text.match(re); if (!m)
    return { value: fallback, source: 'assumed' }; const n = /^[-+]?\d+(?:\.\d+)?$/.test(m[1]) ? Number(m[1]) : wordNumbers[m[1]]; return Number.isFinite(n) ? { value: n, source: 'requested' } : { value: fallback, source: 'assumed' }; }
export function understand(prompt) {
    const t = normalizeText(prompt);
    if (t.length > 12000)
        throw Error('الوصف أطول من الحد المسموح (12,000 حرف).');
    const dim = t.match(/([-+]?\d+(?:\.\d+)?)\s*(?:×|x|\*|في|بـ?)\s*([-+]?\d+(?:\.\d+)?)/);
    const projectType = /(?:مستودع|مخزن|warehouse)/.test(t) ? 'warehouse' : /(?:مكاتب|مكتب اداري|office)/.test(t) ? 'office' : /(?:متجر|محل تجاري|تجز[يئ]ه|retail)/.test(t) ? 'retail' : /شاليه/.test(t) ? 'chalet' : 'villa';
    const residential = ['villa', 'chalet'].includes(projectType);
    const defaultFloors = projectType === 'villa' || projectType === 'office' ? 2 : 1;
    let floors = amount(t, /([-+]?\d+(?:\.\d+)?|ثلاثه?|اربعه?|خمسه?|سته?|سبعه?|ثمانيه?|واحده?)\s*(?:ادوار|طوابق|دور|طابق)/, defaultFloors);
    if (/دورين|طابقين/.test(t)) floors = { value: 2, source: 'requested' };
    if (/دور واحد|طابق واحد/.test(t)) floors = { value: 1, source: 'requested' };
    const beds = residential ? amount(t, /([-+]?\d+(?:\.\d+)?|ثلاثه?|اربعه?|خمسه?|سته?|سبعه?|ثمانيه?|تسعه?|عشره?)\s*(?:غرف(?:ه)?\s*(?:نوم)?)/, projectType === 'chalet' ? 3 : 4) : { value: 0, source: 'derived' };
    const offices = projectType === 'office' ? amount(t, /([-+]?\d+(?:\.\d+)?|ثلاثه?|اربعه?|خمسه?|سته?|سبعه?|ثمانيه?)\s*(?:مكاتب|مكتب)/, 4) : { value: 0, source: 'derived' };
    const parking = amount(t, /([-+]?\d+(?:\.\d+)?|ثلاثه?|اربعه?|خمسه?|سته?|سبعه?|ثمانيه?|تسعه?|عشره?)\s*(?:مواقف|موقف)/, projectType === 'warehouse' ? 2 : 1);
    const street = ['شمال', 'جنوب', 'شرق', 'غرب'].find(d => new RegExp(`(?:شارع|مدخل)[^،.\n]{0,16}${d}`).test(t));
    const priority = /خصوصي/.test(t) ? 'privacy' : /(?:حديق|مسبح|اطلال|خارجي)/.test(t) ? 'outdoor' : /(?:مدمج|اقتصادي|اصغر|اقل مساح)/.test(t) ? 'compact' : 'balanced';
    const style = /كلاسيك/.test(t) ? 'classic' : /(?:مودرن|حديث)/.test(t) ? 'modern' : /صناعي/.test(t) ? 'industrial' : 'unspecified';
    const titles = { villa: 'فيلا الفناء', chalet: 'شاليه الفناء', office: 'مكاتب مسار', warehouse: 'مستودع مسار', retail: 'مساحة تجارية' };
    const brief = {
        prompt: String(prompt), width: dim ? Number(dim[1]) : projectType === 'warehouse' ? 30 : 20, depth: dim ? Number(dim[2]) : projectType === 'warehouse' ? 40 : 25,
        floors: floors.value, bedrooms: beds.value, offices: offices.value, parking: parking.value, street: street || 'جنوب',
        elevator: /مصعد/.test(t) && !/(?:بدون|دون|لا يوجد)\s*مصعد/.test(t), pool: /مسبح/.test(t) && !/(?:بدون|دون|لا يوجد)\s*مسبح/.test(t),
        projectType, priority, style, title: titles[projectType],
        sources: { width: dim ? 'requested' : 'assumed', depth: dim ? 'requested' : 'assumed', floors: floors.source, bedrooms: beds.source, offices: offices.source, parking: parking.source, street: street ? 'requested' : 'assumed', projectType: projectType === 'villa' && !/(?:فيلا|منزل)/.test(t) ? 'assumed' : 'requested' },
        intents: [], unresolved: []
    };
    if (brief.width < 12 || brief.width > 120 || brief.depth < 15 || brief.depth > 160)
        brief.unresolved.push('مولّد التوزيع الحالي يدعم أرضًا مستطيلة بعرض 12–120 م وعمق 15–160 م. عدّل الأبعاد أو استورد مشروع JSON.');
    if (!Number.isInteger(brief.floors) || brief.floors < 1 || brief.floors > 8)
        brief.unresolved.push('هذه النسخة تدعم من دور واحد إلى ثمانية أدوار مفاهيمية.');
    if (residential && (!Number.isInteger(brief.bedrooms) || brief.bedrooms < 1 || brief.bedrooms > 16))
        brief.unresolved.push('المشاريع السكنية تدعم من غرفة نوم واحدة إلى 16 غرفة نوم.');
    if (projectType === 'office' && (!Number.isInteger(brief.offices) || brief.offices < 1 || brief.offices > 20))
        brief.unresolved.push('مشاريع المكاتب تدعم من مكتب واحد إلى 20 مكتبًا في البرنامج المفاهيمي.');
    if (/(?:مجلس)[^،.\n]{0,28}(?:قريب|قرب)[^،.\n]{0,18}(?:مدخل)/.test(t) || /(?:قرب|قريب)[^،.\n]{0,18}(?:مدخل)[^،.\n]{0,28}(?:مجلس)/.test(t))
        brief.intents.push({ type: 'near-entry', subjectKind: 'majlis', label: 'المجلس قريب من المدخل', source: 'requested' });
    if (/(?:مطبخ|معيش)[^،.\n]{0,34}(?:حديق|مسبح|خارجي|اطلال)/.test(t))
        brief.intents.push({ type: 'garden-edge', subjectKind: /مطبخ/.test(t) ? 'kitchen' : 'living', label: /مطبخ/.test(t) ? 'المطبخ مرتبط بالجهة الخارجية' : 'المعيشة مرتبطة بالجهة الخارجية', source: 'requested' });
    return brief;
}
export function briefIssues(b) { return b.unresolved.filter(x => !x.startsWith('المصعد') && !x.startsWith('المسبح')); }
function room(id, name, kind, x, y, w, d, doorSide = 'east', entry = false) { return { id, name, kind, x: round(x), y: round(y), w: round(w), d: round(d), height: 3, locked: false, doors: [{ id: `${id}-door`, side: doorSide, offset: .5, width: Math.min(.9, Math.min(w, d) * .7), entry }], windows: [], note: '', provenance: 'generated-concept' }; }
export function generate(brief, variant = 0) {
    if (briefIssues(brief).length) throw Error(briefIssues(brief)[0]);
    const residential = ['villa', 'chalet'].includes(brief.projectType || 'villa');
    if (![brief.width, brief.depth].every(Number.isFinite) || brief.width < 12 || brief.width > 120 || brief.depth < 15 || brief.depth > 160 || !Number.isInteger(brief.floors) || brief.floors < 1 || brief.floors > 8 || (residential && (!Number.isInteger(brief.bedrooms) || brief.bedrooms < 1 || brief.bedrooms > 16)) || !['شمال', 'جنوب', 'شرق', 'غرب'].includes(brief.street))
        throw Error('الأبعاد أو أعداد الأدوار والغرف خارج النطاق المدعوم.');
    const sideways = ['شرق', 'غرب'].includes(brief.street), W = sideways ? brief.depth : brief.width, D = sideways ? brief.width : brief.depth;
    const sideSetback = Math.max(2, Math.min(4, W * .08)), endSetback = Math.max(3, Math.min(5, D * .10));
    const bx = round(sideSetback), by = round(endSetback), bw = round(W - sideSetback * 2), bd = round(D - endSetback * 2), hw = Math.max(1.5, Math.min(2.2, bw * .08));
    const bias = variant === 1 ? .06 : variant === 2 ? -.06 : 0, lw = round((bw - hw) * (.50 + bias)), rw = round(bw - lw - hw);
    const levels = [];
    let remainingBeds = brief.bedrooms || 0, remainingOffices = brief.offices || 0;
    const projectType = brief.projectType || 'villa';
    const cfgFor = f => {
        if (projectType === 'warehouse') return f === 0 ? [{ name: 'منطقة التخزين الرئيسية', kind: 'warehouse' }, { name: 'الاستلام والتحميل', kind: 'loading' }, { name: 'مكتب التشغيل', kind: 'office' }, { name: 'خدمات العاملين', kind: 'service' }, { name: 'دورة مياه', kind: 'bath' }] : [{ name: `مكتب إدارة الدور ${f}`, kind: 'office' }, { name: 'غرفة اجتماع', kind: 'meeting' }, { name: 'خدمات', kind: 'service' }];
        if (projectType === 'retail') return f === 0 ? [{ name: 'صالة العرض', kind: 'retail' }, { name: 'مخزن خلفي', kind: 'storage' }, { name: 'مكتب الإدارة', kind: 'office' }, { name: 'خدمات', kind: 'service' }, { name: 'دورة مياه', kind: 'bath' }] : [{ name: `صالة عرض ${f + 1}`, kind: 'retail' }, { name: 'مخزن', kind: 'storage' }, { name: 'خدمات', kind: 'service' }];
        if (projectType === 'office') {
            const floorsLeft = brief.floors - f, officesHere = Math.max(0, Math.ceil(remainingOffices / floorsLeft)); remainingOffices -= officesHere;
            const start = Math.max(1, (brief.offices || 4) - remainingOffices - officesHere + 1), list = Array.from({ length: officesHere }, (_, i) => ({ name: `مكتب ${start + i}`, kind: 'office' }));
            if (f === 0) list.unshift({ name: 'الاستقبال', kind: 'reception' });
            list.push({ name: 'غرفة اجتماع', kind: 'meeting' }, { name: 'استراحة وتحضير', kind: 'kitchen' }, { name: 'خدمات', kind: 'bath' }); return list;
        }
        if (f === 0 && brief.floors > 1) return [{ name: 'مجلس الضيوف', kind: 'majlis' }, { name: 'غرفة الطعام', kind: 'dining' }, { name: 'المعيشة العائلية', kind: 'living' }, { name: 'المدخل والخدمات', kind: 'service' }, { name: 'مطبخ مفتوح', kind: 'kitchen' }, { name: 'دورة مياه الضيوف', kind: 'bath' }];
        const floorsLeft = brief.floors - f, bedsHere = Math.ceil(remainingBeds / floorsLeft), start = (brief.bedrooms || 1) - remainingBeds + 1;
        const list = Array.from({ length: bedsHere }, (_, i) => ({ name: `غرفة نوم ${start + i}`, kind: 'bedroom' })); remainingBeds -= bedsHere;
        if (f === 0) list.push({ name: projectType === 'chalet' ? 'المعيشة والمجلس' : 'المعيشة العائلية', kind: 'living' }, { name: 'المطبخ', kind: 'kitchen' }, { name: 'مجلس الضيوف', kind: 'majlis' });
        else list.push({ name: 'صالة عائلية', kind: 'living' });
        list.push({ name: 'دورة مياه', kind: 'bath' }); return list;
    };
    for (let f = 0; f < brief.floors; f++) {
        const r = [], prefix = `l${f}`, configs = cfgFor(f), leftCfg = configs.filter((_, i) => i % 2 === 0), rightCfg = configs.filter((_, i) => i % 2 === 1);
        const coreD = Math.min(4.8, Math.max(3.6, bd * .28)), flip = variant === 2, rightUsableD = bd - coreD;
        leftCfg.forEach((c, i) => { const y1 = round(by + i * bd / leftCfg.length), y2 = round(by + (i + 1) * bd / leftCfg.length); r.push(room(`${prefix}-room-${configs.indexOf(c)}`, c.name, c.kind, bx, y1, lw, round(y2 - y1), 'east')); });
        rightCfg.forEach((c, i) => { const y1 = round(by + i * rightUsableD / Math.max(rightCfg.length, 1)), y2 = round(by + (i + 1) * rightUsableD / Math.max(rightCfg.length, 1)); r.push(room(`${prefix}-room-${configs.indexOf(c)}`, c.name, c.kind, bx + lw + hw, y1, rw, round(y2 - y1), 'west')); });
        r.push(room(`${prefix}-hall`, projectType === 'warehouse' ? 'ممر التشغيل' : 'ممر التوزيع', 'hall', bx + lw, by, hw, bd, 'south', f === 0));
        if (f === 0) r.find(x => x.kind === 'hall').doors.push({ id: `${prefix}-rear-door`, side: 'north', offset: .5, width: 1, entry: true });
        const coreX = bx + lw + hw, coreY = by + bd - coreD;
        if (brief.elevator) {
            const liftD = Math.min(1.9, coreD * .42), stairD = round(coreD - liftD - .18);
            const stair = room(`${prefix}-stairs`, 'الدرج الرئيسي', 'stairs', coreX, coreY, rw, stairD, 'west'); stair.locked = true; r.push(stair);
            const lift = room(`${prefix}-elevator`, 'المصعد', 'elevator', coreX, round(coreY + stairD + .18), Math.min(2.2, rw), liftD, 'west'); lift.locked = true; lift.provenance = 'requested-concept-core'; r.push(lift);
        } else { const stair = room(`${prefix}-stairs`, 'الدرج الرئيسي', 'stairs', coreX, coreY, rw, coreD, 'west'); stair.locked = true; r.push(stair); }
        if (flip) for (const s of r) { s.x = round(W - s.x - s.w); s.doors.forEach(d => { if (d.side === 'east') d.side = 'west'; else if (d.side === 'west') d.side = 'east'; else d.offset = 1 - d.offset; }); }
        levels.push({ id: prefix, name: f === 0 ? 'الدور الأرضي' : `الدور ${f}`, elevation: round(f * 3.3), height: 3.3, rooms: r });
    }
    if (brief.street !== 'جنوب') for (const l of levels) for (const r of l.rooms) {
        const { x, y, w, d } = r, direction = brief.street;
        if (direction === 'شمال') { r.x = round(brief.width - x - w); r.y = round(brief.depth - y - d); }
        if (direction === 'شرق') { r.x = round(brief.width - y - d); r.y = x; r.w = d; r.d = w; }
        if (direction === 'غرب') { r.x = y; r.y = round(brief.depth - x - w); r.w = d; r.d = w; }
        for (const door of r.doors) { const old = door.side, maps = { شمال: { south: 'north', north: 'south', east: 'west', west: 'east' }, شرق: { south: 'east', north: 'west', east: 'north', west: 'south' }, غرب: { south: 'west', north: 'east', east: 'south', west: 'north' } }; door.side = maps[direction]?.[old] || old; if (direction === 'شمال' || direction === 'شرق' && ['east', 'west'].includes(old) || direction === 'غرب' && ['north', 'south'].includes(old)) door.offset = round(1 - door.offset); }
    }
    const featureRect = (type, name) => {
        const pad = .45, rear = brief.street === 'جنوب' ? 'north' : brief.street === 'شمال' ? 'south' : brief.street === 'شرق' ? 'west' : 'east';
        if (['north', 'south'].includes(rear)) { const w = Math.min(6, brief.width - 2), d = Math.min(2.1, Math.max(1.4, endSetback - .8)); return { id: `${type}-1`, type, name, x: round((brief.width - w) / 2), y: rear === 'north' ? round(brief.depth - d - pad) : pad, w: round(w), d: round(d), locked: true, provenance: 'requested-concept-feature' }; }
        const w = Math.min(2.1, Math.max(1.4, sideSetback - .55)), d = Math.min(6, brief.depth - 2); return { id: `${type}-1`, type, name, x: rear === 'east' ? round(brief.width - w - pad) : pad, y: round((brief.depth - d) / 2), w: round(w), d: round(d), locked: true, provenance: 'requested-concept-feature' };
    };
    const features = []; if (brief.pool) features.push(featureRect('pool', 'مسبح خارجي مفاهيمي'));
    const authoring = authoringDefaults();
    // Add one deterministic hosted window to eligible exterior rooms. This is a concept
    // authoring element, not a daylight/code calculation or a product specification.
    for (const level of levels) {
        const minX=Math.min(...level.rooms.map(r=>r.x)), maxX=Math.max(...level.rooms.map(r=>r.x+r.w)), minY=Math.min(...level.rooms.map(r=>r.y)), maxY=Math.max(...level.rooms.map(r=>r.y+r.d));
        for (const r of level.rooms) {
            if (['hall','stairs','elevator','bath','service','storage','loading','garage'].includes(r.kind)) continue;
            const candidates=[];
            if (Math.abs(r.x-minX)<.01) candidates.push('west'); if (Math.abs(r.x+r.w-maxX)<.01) candidates.push('east');
            if (Math.abs(r.y-minY)<.01) candidates.push('south'); if (Math.abs(r.y+r.d-maxY)<.01) candidates.push('north');
            const side=candidates.find(x=>!(r.doors||[]).some(d=>d.side===x)) || candidates[0]; if(!side) continue;
            const span=sideSpan(r,side), type=windowTypeFor({authoring},authoring.defaults.windowTypeId), width=round(Math.min(type.width,Math.max(.6,span*.45)));
            if(width>span-.12) continue;
            r.windows=[{id:`${r.id}-window-1`,side,offset:.5,width,height:Math.min(type.height,r.height-.25),sill:Math.min(type.sill,Math.max(.2,r.height-type.height-.2)),typeId:type.id,locked:false,provenance:'generated-concept-window'}];
        }
    }
    const requirements = [
        { id: 'r-floors', label: `${brief.floors} أدوار إجمالًا`, type: 'floors', value: brief.floors, locked: true, source: brief.sources.floors },
        ...(residential ? [{ id: 'r-beds', label: `${brief.bedrooms} غرف نوم`, type: 'bedrooms', value: brief.bedrooms, locked: true, source: brief.sources.bedrooms }] : []),
        { id: 'r-site', label: `أرض ${brief.width} × ${brief.depth} م`, type: 'site', value: [brief.width, brief.depth], locked: true, source: brief.sources.width },
        ...(brief.elevator ? [{ id: 'r-elevator', label: 'وجود مصعد ضمن النواة الرأسية', type: 'feature', value: 'elevator', locked: true, source: 'requested' }] : []),
        ...(brief.pool ? [{ id: 'r-pool', label: 'مسبح خارجي مفاهيمي', type: 'feature', value: 'pool', locked: true, source: 'requested' }] : []),
        ...(brief.intents || []).map((x, i) => ({ id: `r-intent-${i}`, label: x.label, type: 'adjacency', value: clone(x), locked: true, source: x.source || 'requested' })),
        ...brief.unresolved.map((label, i) => ({ id: `r-u${i}`, label, type: 'unresolved', locked: true, source: 'requested' }))
    ];
    return { schemaVersion: VERSION, id: uid(), title: brief.title, authoring, site: { width: brief.width, depth: brief.depth, street: brief.street, north: 'up', setback: { front: endSetback, back: endSetback, left: sideSetback, right: sideSetback }, setbackSource: 'concept-assumption-not-code', features }, brief: clone(brief), requirements, levels, comments: [], references: [], design: { stage: 'concept', projectType, priority: brief.priority || 'balanced', style: brief.style || 'unspecified', generatedVariant: variant }, createdAt: new Date().toISOString() };
}
const finite = n => typeof n === 'number' && Number.isFinite(n);
const safeString = (s, max = 500) => typeof s === 'string' && s.length <= max;
export function roomPolygon(r) { return Array.isArray(r.footprint) && r.footprint.length >= 3 ? r.footprint.map(p=>[Number(p[0]),Number(p[1])]) : [[r.x,r.y],[r.x+r.w,r.y],[r.x+r.w,r.y+r.d],[r.x,r.y+r.d]]; }
function signedPolygonArea(poly) { let a=0; for(let i=0;i<poly.length;i++){const p=poly[i],q=poly[(i+1)%poly.length];a+=p[0]*q[1]-q[0]*p[1];} return a/2; }
export function polygonArea(poly) { return Math.abs(signedPolygonArea(poly)); }
const cross=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
function onSegment(p,a,b,tol=.002){const length=Math.hypot(b[0]-a[0],b[1]-a[1]);return length>0&&Math.abs(cross(a,b,p))/length<=tol&&p[0]>=Math.min(a[0],b[0])-tol&&p[0]<=Math.max(a[0],b[0])+tol&&p[1]>=Math.min(a[1],b[1])-tol&&p[1]<=Math.max(a[1],b[1])+tol;}
export function pointInPolygon(point,poly,includeBoundary=true){if(poly.some((a,i)=>onSegment(point,a,poly[(i+1)%poly.length])))return includeBoundary;let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if(((a[1]>point[1])!==(b[1]>point[1]))&&(point[0]<(b[0]-a[0])*(point[1]-a[1])/(b[1]-a[1])+a[0]))inside=!inside;}return inside;}
function segmentsProperlyIntersect(a,b,c,d){const ab1=cross(a,b,c),ab2=cross(a,b,d),cd1=cross(c,d,a),cd2=cross(c,d,b);return ((ab1>0&&ab2<0)||(ab1<0&&ab2>0))&&((cd1>0&&cd2<0)||(cd1<0&&cd2>0));}
function polygonSimple(poly){
 for(let i=0;i<poly.length;i++)for(let j=i+1;j<poly.length;j++)if(Math.hypot(poly[i][0]-poly[j][0],poly[i][1]-poly[j][1])<.001)return false;
 for(let i=0;i<poly.length;i++){const a=poly[i],b=poly[(i+1)%poly.length],c=poly[(i+2)%poly.length];if(Math.abs(cross(a,b,c))<1e-8&&(b[0]-a[0])*(c[0]-b[0])+(b[1]-a[1])*(c[1]-b[1])<0)return false;
  for(let j=i+1;j<poly.length;j++){if(j===(i+1)%poly.length||i===(j+1)%poly.length)continue;const c=poly[j],d=poly[(j+1)%poly.length];if(segmentsProperlyIntersect(a,b,c,d)||onSegment(c,a,b)||onSegment(d,a,b)||onSegment(a,c,d)||onSegment(b,c,d))return false;}
 }return true;
}
function polygonOrthogonal(poly){return poly.every((p,i)=>{const q=poly[(i+1)%poly.length];return Math.abs(p[0]-q[0])<=.002||Math.abs(p[1]-q[1])<=.002;});}
function footprintBounds(poly){const xs=poly.map(p=>p[0]),ys=poly.map(p=>p[1]);return{x:Math.min(...xs),y:Math.min(...ys),w:Math.max(...xs)-Math.min(...xs),d:Math.max(...ys)-Math.min(...ys)};}
function pointStrictlyInside(point,poly){return pointInPolygon(point,poly,false);}
/** Reject hostile/unbounded documents before rendering or saving. */
export function assertModel(m) {
    if (!m || m.schemaVersion !== VERSION || !safeString(m.id, 100) || !safeString(m.title, 120))
        throw Error('ملف المشروع غير صالح أو إصداره غير مدعوم.');
    if (!m.site || ![m.site.width, m.site.depth].every(n => finite(n) && n >= 4 && n <= 240))
        throw Error('أبعاد الأرض غير صالحة.');
    if (m.authoring !== undefined) {
        const a=m.authoring, typeIds=new Set();
        if (m.authoring?.schema !== 'masar-authoring-1' || !Array.isArray(a.wallTypes) || a.wallTypes.length<1 || a.wallTypes.length>20 || !Array.isArray(a.windowTypes) || a.windowTypes.length<1 || a.windowTypes.length>20 || !a.defaults) throw Error('بيانات التأليف المعماري غير صالحة.');
        for(const wt of a.wallTypes){ if(!safeString(wt.id,100)||typeIds.has(wt.id)||!safeString(wt.name,160)||!['external','internal'].includes(wt.classification)||!finite(wt.totalThickness)||wt.totalThickness<=0||wt.totalThickness>1||!Array.isArray(wt.layers)||wt.layers.length<1||wt.layers.length>12) throw Error('نوع جدار غير صالح.'); typeIds.add(wt.id); let sum=0; const layerIds=new Set();for(const layer of wt.layers){if(!safeString(layer.id,100)||layerIds.has(layer.id)||!safeString(layer.name,160)||!['finish','core','insulation','air','membrane','other'].includes(layer.function)||!finite(layer.thickness)||layer.thickness<=0||layer.thickness>.8)throw Error('طبقة جدار غير صالحة.');layerIds.add(layer.id);sum+=layer.thickness;} if(Math.abs(sum-wt.totalThickness)>.002)throw Error('مجموع طبقات الجدار لا يساوي السماكة الكلية.'); }
        for(const w of a.windowTypes){if(!safeString(w.id,100)||typeIds.has(w.id)||!safeString(w.name,160)||![w.width,w.height,w.sill].every(finite)||w.width<=0||w.height<=0||w.sill<0||w.width>8||w.height>5)throw Error('نوع نافذة غير صالح.');typeIds.add(w.id);}
        if(!a.wallTypes.some(x=>x.id===a.defaults.externalWallTypeId&&x.classification==='external')||!a.wallTypes.some(x=>x.id===a.defaults.internalWallTypeId&&x.classification==='internal')||!a.windowTypes.some(x=>x.id===a.defaults.windowTypeId)) throw Error('النوع الافتراضي في التأليف غير موجود أو تصنيفه لا يطابق الاستخدام.');
        for(const k of ['structure','mep','fire','accessibility','regulatory'])if(a.disciplineStatus?.[k]!=='unchecked')throw Error('لا يمكن لبيانات التأليف ادعاء فحص التخصصات غير المدعومة.');
    }
    if (!Array.isArray(m.levels) || m.levels.length < 1 || m.levels.length > 8)
        throw Error('عدد الأدوار غير صالح.');
    const ids = new Set();
    let count = 0;
    for (const l of m.levels) {
        if (!safeString(l.id, 100) || ids.has(l.id) || !safeString(l.name, 120) || !finite(l.elevation) || l.elevation < 0 || l.elevation > 100 || !finite(l.height) || l.height < 2 || l.height > 6 || !Array.isArray(l.rooms) || l.rooms.length===0)
            throw Error('بيانات الدور غير صالحة.');
        ids.add(l.id);
        for (const r of l.rooms) {
            if (++count > 200 || !safeString(r.id, 100) || ids.has(r.id) || !safeString(r.name, 120) || !Object.hasOwn(KINDS, r.kind))
                throw Error('معرّف غرفة أو نوعها غير صالح.');
            ids.add(r.id);
            if (![r.x, r.y, r.w, r.d, r.height].every(finite) || r.w <= 0 || r.d <= 0 || r.w > 200 || r.d > 200 || r.height < 1 || r.height > 6 || Math.abs(r.x) > 300 || Math.abs(r.y) > 300)
                throw Error('هندسة الغرفة غير صالحة.');
            if (r.footprint !== undefined) {
                if(!Array.isArray(r.footprint)||r.footprint.length<4||r.footprint.length>24||!r.footprint.every(p=>Array.isArray(p)&&p.length===2&&p.every(finite))) throw Error('حدود المساحة غير المستطيلة غير صالحة.');
                if(!polygonOrthogonal(r.footprint)||!polygonSimple(r.footprint)||polygonArea(r.footprint)<.05) throw Error('الحدود غير المستطيلة يجب أن تكون مضلعًا متعامدًا بسيطًا موجب المساحة.');
                const b=footprintBounds(r.footprint); if([b.x-r.x,b.y-r.y,b.w-r.w,b.d-r.d].some(v=>Math.abs(v)>.003)) throw Error('صندوق حدود المساحة لا يطابق مضلعها.');
            }
            if (typeof r.locked !== 'boolean' || !Array.isArray(r.doors) || r.doors.length > 10 || (r.windows!==undefined&&!Array.isArray(r.windows)) || (r.windows?.length||0)>12 || !safeString(r.note ?? '', 2000))
                throw Error('خصائص الغرفة غير صالحة.');
            for (const d of r.doors) {
                if (!safeString(d.id, 130) || ids.has(d.id) || !['east', 'west', 'north', 'south'].includes(d.side) || !finite(d.offset) || d.offset < 0 || d.offset > 1 || !finite(d.width) || d.width <= 0 || d.width > 5 || typeof d.entry !== 'boolean' || (d.height!==undefined&&(!finite(d.height)||d.height<=0||d.height>r.height)))
                    throw Error('بيانات الباب غير صالحة.');
                ids.add(d.id);
            }
            for (const w of r.windows || []) {
                if(!safeString(w.id,130)||ids.has(w.id)||!effectiveAuthoring(m).windowTypes.some(t=>t.id===w.typeId)||!['east','west','north','south'].includes(w.side)||!finite(w.offset)||w.offset<0||w.offset>1||![w.width,w.height,w.sill].every(finite)||w.width<=0||w.width>8||w.height<=0||w.height>5||w.sill<0||w.sill+w.height>r.height+.002||!safeString(w.typeId||'',100)||typeof w.locked!=='boolean') throw Error('بيانات النافذة غير صالحة.');
                ids.add(w.id);
            }
        }
    }
    if (!m.brief || !safeString(m.brief.prompt, 12000) || !Array.isArray(m.requirements) || m.requirements.length > 80)
        throw Error('متطلبات المشروع غير صالحة.');
    for (const r of m.requirements) {
        if (!safeString(r.id, 100) || !safeString(r.label, 1000) || !['floors', 'bedrooms', 'site', 'feature', 'adjacency', 'unresolved', 'custom'].includes(r.type) || typeof r.locked !== 'boolean')
            throw Error('بند متطلب غير صالح.');
    }
    if (m.site.features !== undefined) {
        if (!Array.isArray(m.site.features) || m.site.features.length > 30)
            throw Error('عناصر الموقع غير صالحة.');
        for (const f of m.site.features) {
            if (!safeString(f.id, 100) || !safeString(f.name, 150) || !['pool', 'parking', 'garden', 'terrace'].includes(f.type) || ![f.x, f.y, f.w, f.d].every(finite) || f.w <= 0 || f.d <= 0 || f.w > 200 || f.d > 200 || typeof f.locked !== 'boolean')
                throw Error('عنصر موقع غير صالح.');
        }
    }
    if (m.design !== undefined) {
        if (!m.design || !['concept', 'development', 'review'].includes(m.design.stage) || !['villa', 'chalet', 'office', 'warehouse', 'retail'].includes(m.design.projectType || 'villa') || !['balanced', 'privacy', 'outdoor', 'compact'].includes(m.design.priority || 'balanced') || !safeString(m.design.style || 'unspecified', 40))
            throw Error('إعدادات التصميم غير صالحة.');
    }
    if (!Array.isArray(m.comments) || m.comments.length > 200)
        throw Error('تعليقات المشروع غير صالحة.');
    for (const c of m.comments)
        if (!safeString(c.id, 100) || !safeString(c.roomId, 100) || !safeString(c.text, 2000) || !safeString(c.author, 120) || !safeString(c.at, 80) || typeof c.resolved !== 'boolean')
            throw Error('تعليق غير صالح.');
    if (!Array.isArray(m.references) || m.references.length > 5)
        throw Error('مراجع المشروع غير صالحة.');
    for (const ref of m.references) {
        if (ref.type !== 'dxf' || !safeString(ref.name, 150) || !Array.isArray(ref.lines) || ref.lines.length > 3000 || !finite(ref.scale) || ref.scale <= 0 || ref.scale > 1000)
            throw Error('مرجع رسم غير صالح.');
        for (const line of ref.lines)
            if (!Array.isArray(line) || line.length !== 4 || !line.every(n => finite(n) && Math.abs(n) < 1e7))
                throw Error('خط مرجعي غير صالح.');
    }
    return m;
}
const rawArea = r => Array.isArray(r.footprint)&&r.footprint.length>=3 ? polygonArea(r.footprint) : r.w * r.d;
export const area = r => round(rawArea(r));
export function totals(m) { const rooms = m.levels.flatMap(l => l.rooms), landArea = round(m.site.width * m.site.depth), floorArea = round(rooms.reduce((a, r) => a + rawArea(r), 0)), footprint = round(m.levels[0].rooms.reduce((a, r) => a + rawArea(r), 0)), circulation = round(rooms.filter(r => ['hall', 'stairs', 'elevator'].includes(r.kind)).reduce((a, r) => a + rawArea(r), 0)); return { floorArea, footprint, landArea, outdoorArea: round(Math.max(0, landArea - footprint)), bedrooms: rooms.filter(r => r.kind === 'bedroom').length, offices: rooms.filter(r => r.kind === 'office').length, rooms: rooms.filter(r => !['hall', 'stairs', 'elevator'].includes(r.kind)).length, circulation, circulationPct: floorArea ? round(circulation / floorArea * 100) : 0, coveragePct: landArea ? round(footprint / landArea * 100) : 0, features: (m.site.features || []).length }; }
const clamp = (v, lo = 0, hi = 100) => Math.max(lo, Math.min(hi, v));
export const centroid = r => { const poly=roomPolygon(r); if(!r.footprint)return [r.x+r.w/2,r.y+r.d/2]; const signed=signedPolygonArea(poly); if(Math.abs(signed)<1e-9)return [r.x+r.w/2,r.y+r.d/2]; let cx=0,cy=0; for(let i=0;i<poly.length;i++){const a=poly[i],b=poly[(i+1)%poly.length],f=a[0]*b[1]-b[0]*a[1];cx+=(a[0]+b[0])*f;cy+=(a[1]+b[1])*f;} return [cx/(6*signed),cy/(6*signed)]; };
export function gardenSide(m) { return m.site.street === 'جنوب' ? 'north' : m.site.street === 'شمال' ? 'south' : m.site.street === 'شرق' ? 'west' : 'east'; }
export function entryPoint(m) { const l = m.levels[0], entries = l.rooms.flatMap(r => r.doors.filter(d => d.entry).map(d => doorPoint(r, d))); if (entries.length) return entries[0]; return m.site.street === 'جنوب' ? [m.site.width / 2, 0] : m.site.street === 'شمال' ? [m.site.width / 2, m.site.depth] : m.site.street === 'شرق' ? [m.site.width, m.site.depth / 2] : [0, m.site.depth / 2]; }
export function distanceToEntry(m, r) { const a = entryPoint(m), b = centroid(r); return Math.hypot(a[0] - b[0], a[1] - b[1]); }
export function touchesGardenEdge(m, r, tolerance = .15) { const side = gardenSide(m), l = m.levels.find(l => l.rooms.includes(r)) || m.levels[0], xs = l.rooms.map(x => [x.x, x.x + x.w]).flat(), ys = l.rooms.map(x => [x.y, x.y + x.d]).flat(), minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys); return side === 'north' ? Math.abs(r.y + r.d - maxY) <= tolerance : side === 'south' ? Math.abs(r.y - minY) <= tolerance : side === 'east' ? Math.abs(r.x + r.w - maxX) <= tolerance : Math.abs(r.x - minX) <= tolerance; }
export function requirementStatus(m, req) {
    if (req.type === 'feature') { const present = req.value === 'elevator' ? m.levels.every(l => l.rooms.some(r => r.kind === 'elevator')) : req.value === 'pool' ? (m.site.features || []).some(f => f.type === 'pool') : false; return { measurable: true, satisfied: present, detail: present ? 'موجود في النموذج' : 'غير موجود في النموذج' }; }
    if (req.type !== 'adjacency' || !req.value) return { measurable: false, satisfied: null, detail: 'غير قابل للقياس آليًا' };
    const subjects = m.levels.flatMap(l => l.rooms).filter(r => r.kind === req.value.subjectKind); if (!subjects.length) return { measurable: true, satisfied: false, detail: 'العنصر المطلوب غير موجود' };
    if (req.value.type === 'near-entry') { const ground = m.levels[0].rooms.filter(r => !['hall', 'stairs', 'elevator'].includes(r.kind)), sorted = [...ground].sort((a,b)=>distanceToEntry(m,a)-distanceToEntry(m,b)), cutoff = Math.max(1, Math.ceil(sorted.length * .45)), ids = new Set(sorted.slice(0, cutoff).map(r=>r.id)), ok = subjects.some(r => ids.has(r.id)); return { measurable: true, satisfied: ok, detail: ok ? 'ضمن أقرب مساحات للمدخل' : 'بعيد نسبيًا عن المدخل' }; }
    if (req.value.type === 'garden-edge') { const ok = subjects.some(r => touchesGardenEdge(m, r)); return { measurable: true, satisfied: ok, detail: ok ? 'على واجهة الجهة الخارجية' : 'ليس على واجهة الجهة الخارجية' }; }
    return { measurable: false, satisfied: null, detail: 'علاقة غير مدعومة في القياس' };
}
export function designMetrics(m) {
    assertModel(m); const t = totals(m), rooms = m.levels.flatMap(l => l.rooms), diag = Math.hypot(m.site.width, m.site.depth) || 1;
    const bedrooms = rooms.filter(r => r.kind === 'bedroom'), publicRooms = rooms.filter(r => ['majlis', 'reception', 'retail', 'living'].includes(r.kind)), usable = rooms.filter(r => !['hall','stairs','elevator','bath','service'].includes(r.kind));
    const avg = xs => xs.length ? xs.reduce((a,x)=>a+x,0)/xs.length : 0;
    const privateDistance = bedrooms.length ? avg(bedrooms.map(r=>distanceToEntry(m,r))) / diag * 100 : 65;
    const publicNear = publicRooms.length ? 100 - avg(publicRooms.map(r=>distanceToEntry(m,r))) / diag * 100 : 70;
    const privacy = clamp(privateDistance * .62 + publicNear * .38);
    const movement = clamp(100 - t.circulationPct * 1.8 - avg(usable.map(r=>distanceToEntry(m,r))) / diag * 28 + 25);
    let edgeCount = 0, eligible = 0; for (const l of m.levels) { const xs=l.rooms.map(r=>[r.x,r.x+r.w]).flat(), ys=l.rooms.map(r=>[r.y,r.y+r.d]).flat(), minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys); for (const r of l.rooms.filter(r=>!['hall','stairs','elevator','bath','service'].includes(r.kind))) { eligible++; if (Math.abs(r.x-minX)<.15||Math.abs(r.x+r.w-maxX)<.15||Math.abs(r.y-minY)<.15||Math.abs(r.y+r.d-maxY)<.15) edgeCount++; } }
    const daylightProxy = eligible ? clamp(edgeCount / eligible * 100) : 0, outdoor = clamp((t.outdoorArea / t.landArea) * 100 * 1.7), efficiency = clamp(100 - t.circulationPct * 2.2);
    const measurable = m.requirements.map(r=>requirementStatus(m,r)).filter(x=>x.measurable), requirements = measurable.length ? measurable.filter(x=>x.satisfied).length / measurable.length * 100 : 100;
    const priority = m.design?.priority || 'balanced', weights = priority === 'privacy' ? [0.34,.19,.12,.10,.25] : priority === 'outdoor' ? [.17,.18,.30,.10,.25] : priority === 'compact' ? [.13,.27,.10,.30,.20] : [.22,.23,.18,.17,.20];
    const overall = clamp(privacy*weights[0] + movement*weights[1] + outdoor*weights[2] + efficiency*weights[3] + requirements*weights[4]);
    return { privacy: round(privacy), movement: round(movement), outdoor: round(outdoor), efficiency: round(efficiency), daylightProxy: round(daylightProxy), requirements: round(requirements), overall: round(overall), priority, note: 'مؤشرات مفاهيمية للمقارنة داخل مسار؛ ليست فحص كود أو اعتمادًا هندسيًا.' };
}
export function impactSummary(before, after) { const bt=totals(before), at=totals(after), bi=validate(before), ai=validate(after), bset=new Set(bi.map(i=>i.id)), aset=new Set(ai.map(i=>i.id)), changes=diffModels(before,after); return { changes, affectedIds: changes.map(c=>c.id), floorAreaDelta: round(at.floorArea-bt.floorArea), footprintDelta: round(at.footprint-bt.footprint), circulationDelta: round(at.circulation-bt.circulation), scoreDelta: round(designMetrics(after).overall-designMetrics(before).overall), newIssues: ai.filter(i=>!bset.has(i.id)), resolvedIssues: bi.filter(i=>!aset.has(i.id)), beforeMetrics: designMetrics(before), afterMetrics: designMetrics(after) }; }
export function createAlternatives(base) {
    assertModel(base); const make = (label, description, strategy) => { let alt=clone(base); for (const l of alt.levels) { const free=l.rooms.filter(r=>!r.locked&&!['hall','stairs','elevator'].includes(r.kind)); if (free.length<2) continue; let subject, target; if (strategy==='privacy') { subject=free.find(r=>r.kind==='bedroom'); const candidates=free.filter(r=>r.id!==subject?.id).sort((a,b)=>distanceToEntry(alt,b)-distanceToEntry(alt,a)); target=candidates[0]; } else if (strategy==='entry') { subject=free.find(r=>['majlis','reception','retail'].includes(r.kind)); const candidates=free.filter(r=>r.id!==subject?.id).sort((a,b)=>distanceToEntry(alt,a)-distanceToEntry(alt,b)); target=candidates[0]; } else { subject=free.find(r=>['living','kitchen'].includes(r.kind)); const candidates=free.filter(r=>r.id!==subject?.id).sort((a,b)=>Number(touchesGardenEdge(alt,b))-Number(touchesGardenEdge(alt,a))); target=candidates.at(-1); } if (subject&&target&&subject.id!==target.id) { try { const p=propose(alt,{type:'swap',roomId:subject.id,targetId:target.id}); if(!p.blockers.length) alt=p.candidate; } catch {} } } return { label, description, strategy, model:alt, metrics:designMetrics(alt) }; };
    return [{ label:'التوزيع الحالي',description:'مرجع المقارنة كما هو الآن.',strategy:'current',model:clone(base),metrics:designMetrics(base)}, make('خصوصية أعلى','يحاول إبعاد غرف النوم وتحسين فصل الخاص عن الوصول العام.','privacy'), make('استقبال أقرب','يحاول تقريب المجلس/الاستقبال من المدخل مع إبقاء العناصر المثبتة.','entry'), make('ارتباط خارجي','يحاول تقريب المعيشة أو المطبخ من جهة الحديقة/الخارج.','outdoor')];
}
/** Exact positive-area overlap for supported orthogonal polygons (not centroid guessing). */
export function overlap(a,b){
 const left=Math.max(a.x,b.x),right=Math.min(a.x+a.w,b.x+b.w),bottom=Math.max(a.y,b.y),top=Math.min(a.y+a.d,b.y+b.d);if(right-left<=.002||top-bottom<=.002)return false;
 if(!a.footprint&&!b.footprint)return true;
 const A=roomPolygon(a),B=roomPolygon(b),xs=[...new Set([left,right,...A.map(p=>p[0]),...B.map(p=>p[0])].filter(x=>x>=left&&x<=right))].sort((x,y)=>x-y);
 const intervals=(poly,x)=>{const ys=[];for(let i=0;i<poly.length;i++){const p=poly[i],q=poly[(i+1)%poly.length];if((p[0]<=x&&q[0]>x)||(q[0]<=x&&p[0]>x))ys.push(p[1]+(q[1]-p[1])*(x-p[0])/(q[0]-p[0]));}ys.sort((a,b)=>a-b);return ys;};
 for(let i=1;i<xs.length;i++){if(xs[i]-xs[i-1]<=.002)continue;const x=(xs[i]+xs[i-1])/2,aa=intervals(A,x),bb=intervals(B,x);for(let j=0;j<aa.length;j+=2)for(let k=0;k<bb.length;k+=2)if(Math.min(aa[j+1],bb[k+1])-Math.max(aa[j],bb[k])>.002)return true;}
 return false;
}
export function doorPoint(r, d) { return openingPoint(r,d); }
export function windowPoint(r,w){ return openingPoint(r,w); }
function openingFitsBoundary(r,o){const [x,y]=openingPoint(r,o),v=['east','west'].includes(o.side),a=v?[x,y-o.width/2]:[x-o.width/2,y],b=v?[x,y+o.width/2]:[x+o.width/2,y],poly=roomPolygon(r);return poly.some((p,i)=>onSegment(a,p,poly[(i+1)%poly.length],.004)&&onSegment(b,p,poly[(i+1)%poly.length],.004));}
function openingFitsHost(room,opening,rooms){
 const [x,y]=openingPoint(room,opening),v=['east','west'].includes(opening.side),coord=v?x:y,center=v?y:x,points=[];
 for(const r of rooms){const p=roomPolygon(r);for(let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%p.length];if(v?Math.abs(a[0]-b[0])<.002&&Math.abs(a[0]-coord)<.002:Math.abs(a[1]-b[1])<.002&&Math.abs(a[1]-coord)<.002)points.push(v?a[1]:a[0],v?b[1]:b[0]);}}
 const stops=[...new Set(points.map(round))].sort((a,b)=>a-b);return stops.some((n,i)=>i>0&&center-opening.width/2>=stops[i-1]-.002&&center+opening.width/2<=n+.002);
}
function neighbours(r, d, rooms) { const [x, y] = doorPoint(r, d), n = d.side === 'east' ? [.02, 0] : d.side === 'west' ? [-.02, 0] : d.side === 'north' ? [0, .02] : [0, -.02]; const p=[x+n[0],y+n[1]]; return rooms.filter(s => s.id !== r.id && pointInPolygon(p,roomPolygon(s),true)); }
export function validate(m) {
    assertModel(m);
    const issues = [];
    const add = (id, status, message, targets = [], category = 'geometry') => issues.push({ id, status, message, targets, category });
    const all = m.levels.flatMap(l => l.rooms), reachableGlobal = new Set();
    for (const l of m.levels) {
        const graph = new Map(l.rooms.map(r => [r.id, new Set()])), starts = [];
        for (const r of l.rooms) {
            if (r.x < -.002 || r.y < -.002 || r.x + r.w > m.site.width + .002 || r.y + r.d > m.site.depth + .002)
                add(`bounds-${r.id}`, 'error', `${r.name}: جزء من الغرفة خارج الأرض.`, [r.id]);
            if(r.height>l.height+.002)add(`height-${r.id}`,'error',`${r.name}: ارتفاع الغرفة يتجاوز ارتفاع الدور.`,[r.id]);
            if (r.w < 1 || r.d < 1)
                add(`narrow-${r.id}`, 'warning', `${r.name}: أحد الأبعاد أصغر من متر؛ راجع قابلية الاستخدام.`, [r.id]);
            for (const d of r.doors) {
                const span = ['east', 'west'].includes(d.side) ? r.d : r.w;
                if (d.offset * span - d.width / 2 < -.002 || d.offset * span + d.width / 2 > span + .002) {
                    add(`door-fit-${d.id}`, 'error', `${r.name}: الباب لا يتسع داخل الجدار.`, [r.id]);
                    continue;
                }
                if(!openingFitsHost(r,d,l.rooms))add(`host-span-${d.id}`,'error',`${r.name}: عرض الباب يعبر نهاية قطاع الجدار المضيف.`,[r.id,d.id],'openings');
                if(r.footprint && !openingFitsBoundary(r,d)) { add(`door-boundary-${d.id}`,'error',`${r.name}: موضع الباب لا يقع على حدود المساحة غير المستطيلة.`,[r.id,d.id]); continue; }
                const ns = neighbours(r, d, l.rooms);
                ns.forEach(s => { graph.get(r.id).add(s.id); graph.get(s.id).add(r.id); });
                if (d.entry && l.elevation === 0 && ns.length === 0)
                    starts.push(r.id);
                if (!d.entry && ns.length === 0)
                    add(`door-outside-${d.id}`, 'warning', `${r.name}: باب لا يتصل بغرفة مجاورة؛ تحقّق من كونه مدخلًا خارجيًا.`, [r.id], 'connectivity');
            }
            const apertures=[...r.doors.map(d=>({...d,sill:0,height:d.height??2.15})),...(r.windows||[])];
            for(let ai=0;ai<apertures.length;ai++)for(let bi=ai+1;bi<apertures.length;bi++){const a=apertures[ai],b=apertures[bi];if(a.side!==b.side)continue;const span=sideSpan(r,a.side),distance=Math.abs(a.offset-b.offset)*span;if(distance<(a.width+b.width)/2-.002&&Math.min(a.sill+a.height,b.sill+b.height)>Math.max(a.sill,b.sill)+.002)add(`opening-overlap-${a.id}-${b.id}`,'error',`${r.name}: تداخل بين فتحتين على الجدار نفسه.`,[r.id,a.id,b.id],'openings');}
            for(const w of r.windows||[]){
                const span=sideSpan(r,w.side);
                if(!openingFitsHost(r,w,l.rooms))add(`host-span-${w.id}`,'error',`${r.name}: عرض النافذة يعبر نهاية قطاع الجدار المضيف.`,[r.id,w.id],'openings');
                if(w.offset*span-w.width/2<-.002||w.offset*span+w.width/2>span+.002) add(`window-fit-${w.id}`,'error',`${r.name}: النافذة لا تتسع داخل ضلع الاستضافة.`,[r.id,w.id],'openings');
                if(r.footprint&&!openingFitsBoundary(r,w)) add(`window-boundary-${w.id}`,'error',`${r.name}: النافذة لا تقع على حد فعلي للمساحة غير المستطيلة.`,[r.id,w.id],'openings');
                const probe={...w,entry:false}, ns=neighbours(r,probe,l.rooms);
                if(ns.length) add(`window-interior-${w.id}`,'warning',`${r.name}: النافذة تقع على حد مجاور لمساحة داخلية؛ راجع نوع الفتحة.`,[r.id,w.id,...ns.map(x=>x.id)],'openings');
            }
        }
        for (let i = 0; i < l.rooms.length; i++)
            for (let j = i + 1; j < l.rooms.length; j++)
                if (overlap(l.rooms[i], l.rooms[j]))
                    add(`overlap-${l.rooms[i].id}-${l.rooms[j].id}`, 'error', `تداخل بين ${l.rooms[i].name} و${l.rooms[j].name}.`, [l.rooms[i].id, l.rooms[j].id]);
        if (l.elevation > 0) {
            const below = m.levels.filter(p => p.elevation < l.elevation).sort((a, b) => b.elevation - a.elevation)[0];
            for (const r of l.rooms.filter(s => s.kind === 'stairs')) {
                const linked = below?.rooms.find(s => s.kind === 'stairs' && Math.abs(r.x - s.x) < .01 && Math.abs(r.y - s.y) < .01 && Math.abs(r.w - s.w) < .01 && Math.abs(r.d - s.d) < .01 && reachableGlobal.has(s.id));
                if (linked)
                    starts.push(r.id);
                else
                    add(`stair-${r.id}`, 'error', 'موضع الدرج غير متصل بالدور السابق المتاح.', [r.id], 'connectivity');
            }
        }
        const seen = new Set(starts), queue = [...starts];
        for (let k = 0; k < queue.length; k++)
            for (const n of graph.get(queue[k]) || [])
                if (!seen.has(n)) {
                    seen.add(n);
                    queue.push(n);
                }
        seen.forEach(id => reachableGlobal.add(id));
        for (const r of l.rooms)
            if (!seen.has(r.id))
                add(`access-${r.id}`, 'error', `${r.name}: لا يوجد مسار متصل من مدخل الأرضي إلى الغرفة.`, [r.id], 'connectivity');
    }
    for (const f of m.site.features || []) {
        if (f.x < -.002 || f.y < -.002 || f.x + f.w > m.site.width + .002 || f.y + f.d > m.site.depth + .002)
            add(`feature-bounds-${f.id}`, 'error', `${f.name}: جزء من العنصر خارج الأرض.`, [], 'site');
        for (const r of m.levels[0].rooms)
            if (overlap(f, r)) add(`feature-overlap-${f.id}-${r.id}`, 'error', `${f.name} يتداخل مع ${r.name}.`, [r.id], 'site');
    }
    const ts = totals(m);
    for (const req of m.requirements) {
        if (req.type === 'bedrooms' && ts.bedrooms !== req.value)
            add(req.id, 'error', `المطلوب ${req.value} غرف نوم؛ الموجود ${ts.bedrooms}.`, [], 'requirements');
        if (req.type === 'floors' && m.levels.length !== req.value)
            add(req.id, 'error', 'عدد الأدوار لا يطابق المتطلب.', [], 'requirements');
        if (req.type === 'site' && (m.site.width !== req.value?.[0] || m.site.depth !== req.value?.[1]))
            add(req.id, 'error', 'أبعاد الأرض لا تطابق المتطلب.', [], 'requirements');
        if (req.type === 'feature' || req.type === 'adjacency') {
            const status = requirementStatus(m, req);
            if (status.measurable && !status.satisfied) add(req.id, 'warning', `${req.label}: ${status.detail}.`, [], 'requirements');
            if (status.measurable && status.satisfied) add(`checked-${req.id}`, 'checked', `${req.label}: ${status.detail}.`, [], 'requirements');
        }
        if (req.type === 'unresolved' || req.type === 'custom')
            add(req.id, 'unchecked', req.label, [], 'requirements');
    }
    const errorTargets = new Set(issues.filter(i => i.status === 'error').flatMap(i => i.targets));
    for (const r of all) if (!errorTargets.has(r.id)) add(`checked-room-${r.id}`, 'checked', `${r.name}: فُحص التداخل وحدود الأرض والاتصال الهندسي في نموذج مسار ولم يظهر خطأ مانع.`, [r.id], 'model-check');
    add('structure', 'unchecked', 'السلامة الإنشائية والأساسات والأحمال لم تُفحص.', [], 'engineering');
    add('regulatory', 'unchecked', 'الاشتراطات البلدية والارتدادات النظامية لم تُفحص.', [], 'engineering');
    add('fire-life-safety', 'unchecked', 'الحريق والإخلاء وأعداد المخارج ومسافات الهروب لم تُفحص هندسيًا.', [], 'engineering');
    add('accessibility', 'unchecked', 'متطلبات الإتاحة لم تُفحص.', [], 'engineering');
    add('mep', 'unchecked', 'أنظمة الكهرباء والميكانيكا والصحي والتنسيق بينها لم تُصمّم أو تُفحص.', [], 'engineering');
    add('stairs-design', 'unchecked', 'السلم ممثل بحيّز ودرجات عرضية؛ النائمة والقائمة والبسطات والخلوص لم تُصمّم.', all.filter(r => r.kind === 'stairs').map(r => r.id), 'engineering');
    if (all.some(r => r.kind === 'elevator')) add('elevator-design', 'unchecked', 'المصعد ممثل ببئر مفاهيمي؛ الأبعاد الفنية والحفرة والرأس والمعدات ومتطلبات الإنقاذ لم تُصمّم.', all.filter(r => r.kind === 'elevator').map(r => r.id), 'engineering');
    if ((m.site.features || []).some(f => f.type === 'pool')) add('pool-design', 'unchecked', 'المسبح تموضع مفاهيمي فقط؛ الإنشاء والعزل والتصفية والأمان لم تُصمّم.', [], 'engineering');
    return issues;
}
export function diffModels(before, after) { const a = new Map(before.levels.flatMap(l => l.rooms).map(r => [r.id, r])), b = new Map(after.levels.flatMap(l => l.rooms).map(r => [r.id, r])); const changes = []; for (const [id, r] of b) {
    const prev = a.get(id);
    if (!prev) {
        changes.push({ id, name: r.name, kind: 'added' });
        continue;
    }
    const fields = ['name', 'kind', 'x', 'y', 'w', 'd', 'height', 'locked', 'footprint', 'doors', 'windows', 'note'].filter(k => JSON.stringify(prev[k]) !== JSON.stringify(r[k]));
    if (fields.length)
        changes.push({ id, name: r.name, kind: 'changed', fields, before: prev, after: r });
} for (const [id, r] of a)
    if (!b.has(id))
        changes.push({ id, name: r.name, kind: 'removed' });
    for (const [field,name] of [['authoring','نواة التأليف'],['design','إعدادات التصميم'],['site','الموقع']]) if (JSON.stringify(before[field]) !== JSON.stringify(after[field])) changes.push({id:`project:${field}`,name,kind:'changed',fields:[field],before:before[field],after:after[field]});
    return changes; }
export function checkLocks(before, after) {
    for(const r of before.levels.flatMap(l=>l.rooms)){
      const now=after.levels.flatMap(l=>l.rooms).find(x=>x.id===r.id);
      for(const kind of ['windows','doors'])for(const opening of (r[kind]||[]).filter(x=>x.locked)){
        const currentOpening=now?.[kind]?.find(x=>x.id===opening.id);
        if(!currentOpening||JSON.stringify(opening)!==JSON.stringify(currentOpening)||r.x!==now.x||r.y!==now.y||r.w!==now.w||r.d!==now.d||JSON.stringify(r.footprint)!==JSON.stringify(now.footprint))throw Error(kind==='windows'?'نافذة مثبتة تتأثر بهذا التعديل.':'باب مثبت يتأثر بهذا التعديل.');
      }
    }
    for (const old of before.levels.flatMap(l => l.rooms).filter(r => r.locked)) {
        const now = after.levels.flatMap(l => l.rooms).find(r => r.id === old.id);
        if (!now || ['x', 'y', 'w', 'd', 'height', 'kind', 'footprint', 'doors', 'windows'].some(k => JSON.stringify(old[k]) !== JSON.stringify(now[k])))
            throw Error(`العنصر «${old.name}» مثبّت؛ ألغِ تثبيته صراحة قبل تغيير هندسته.`);
    }
    for (const req of before.requirements.filter(r => r.locked)) {
        const now = after.requirements.find(r => r.id === req.id);
        if (!now || JSON.stringify({ ...now, locked: true }) !== JSON.stringify({ ...req, locked: true }))
            throw Error('لا يجوز تغيير متطلب مثبت داخل تعديل هندسي.');
    }
}
export function propose(model, command) {
    const candidate = clone(model), rooms = candidate.levels.flatMap(l => l.rooms), r = rooms.find(r => r.id === command.roomId);
    if (!r) throw Error('اختر الغرفة التي تريد تعديلها.');
    const allowed = ['resize', 'expand', 'move', 'near', 'rename', 'door', 'remove-door', 'window', 'remove-window', 'swap', 'note', 'notch'];
    if (!allowed.includes(command.type)) throw Error('هذا النوع من الأوامر غير مدعوم.');
    if (r.footprint && ['resize','expand','near','swap'].includes(command.type)) throw Error('هذه المساحة غير مستطيلة؛ استخدم تحريك المساحة أو تحرير حدودها بدل تغيير صندوقها بصمت.');
    if (command.type === 'resize') for (const k of ['w', 'd', 'height']) if (command[k] !== undefined) { if (!finite(command[k]) || command[k] <= 0) throw Error('أدخل بُعدًا موجبًا صالحًا.'); r[k] = round(command[k]); }
    if (command.type === 'expand') {
        const n = Number(command.amount); if (!finite(n) || n <= 0 || n > 20) throw Error('مقدار التوسعة يجب أن يكون أكبر من صفر وأقل من 20 مترًا.');
        let direction = command.direction; if (direction === 'garden') direction = gardenSide(candidate); if (direction === 'street') direction = candidate.site.street === 'جنوب' ? 'south' : candidate.site.street === 'شمال' ? 'north' : candidate.site.street === 'شرق' ? 'east' : 'west';
        if (!['east','west','north','south'].includes(direction)) throw Error('اتجاه التوسعة غير واضح.');
        if (direction === 'east') r.w = round(r.w + n); if (direction === 'west') { r.x = round(r.x - n); r.w = round(r.w + n); } if (direction === 'north') r.d = round(r.d + n); if (direction === 'south') { r.y = round(r.y - n); r.d = round(r.d + n); }
    }
    if (command.type === 'move') {
        const nx=command.x===undefined?r.x:Number(command.x), ny=command.y===undefined?r.y:Number(command.y); if(!finite(nx)||!finite(ny)) throw Error('أدخل موقعًا صالحًا.');
        const dx=round(nx-r.x),dy=round(ny-r.y); r.x=round(nx);r.y=round(ny); if(r.footprint) r.footprint=r.footprint.map(p=>[round(p[0]+dx),round(p[1]+dy)]);
    }
    if (command.type === 'rename') { if (!safeString(command.name, 120) || !command.name.trim()) throw Error('اسم الغرفة مطلوب.'); r.name = command.name.trim(); }
    if (command.type === 'note') { if (!safeString(command.note, 2000)) throw Error('الملاحظة طويلة جدًا.'); r.note = command.note; }
    if (command.type === 'door') {
        if(!['east','west','north','south'].includes(command.side))throw Error('جهة الباب غير صالحة.');
        const existing=command.doorId?r.doors.find(d=>d.id===command.doorId):(command.create===true?null:r.doors[0]);
        if(command.doorId&&!existing)throw Error('الباب المحدد غير موجود.');if(existing?.locked)throw Error('الباب مثبت.');
        const next={...(existing||{}),id:existing?.id||uid(),side:command.side,offset:command.offset??existing?.offset??.5,width:command.width??existing?.width??.9,height:command.height??existing?.height??2.15,entry:command.entry??existing?.entry??false};
        if(![next.offset,next.width,next.height].every(finite)||next.offset<0||next.offset>1||next.width<=0||next.height<=0||typeof next.entry!=='boolean')throw Error('أبعاد الباب غير صالحة.');
        if(existing)r.doors=r.doors.map(d=>d.id===existing.id?next:d);else r.doors.push(next);
    }
    if(command.type==='remove-door'){
        const d=r.doors.find(d=>d.id===command.doorId);if(!d)throw Error('الباب غير موجود.');if(d.locked)throw Error('الباب مثبت.');r.doors=r.doors.filter(x=>x.id!==d.id);
    }
    if (command.type === 'window') {
        if(!['east','west','north','south'].includes(command.side)) throw Error('جهة النافذة غير صالحة.'); if(command.typeId&&!effectiveAuthoring(candidate).windowTypes.some(t=>t.id===command.typeId))throw Error('نوع النافذة المحدد غير موجود.'); const type=windowTypeFor(candidate,command.typeId), width=Number(command.width??type.width),height=Number(command.height??type.height),sill=Number(command.sill??type.sill),offset=Number(command.offset??.5);
        if(![width,height,sill,offset].every(finite)||width<=0||height<=0||sill<0||offset<0||offset>1) throw Error('أبعاد النافذة غير صالحة.');
        const existing=(r.windows||[]).find(w=>w.id===command.windowId); if(command.windowId&&!existing)throw Error('النافذة المحددة غير موجودة.'); if(existing?.locked)throw Error('النافذة مثبتة.'); const id=existing?.id||uid(); const next={id,side:command.side,offset:round(offset),width:round(width),height:round(height),sill:round(sill),typeId:type.id,locked:existing?.locked||false,provenance:existing?.provenance||'user-authored-concept-window'};
        r.windows=(r.windows||[]).filter(w=>w.id!==id); r.windows.push(next);
    }
    if (command.type === 'remove-window') { const w=(r.windows||[]).find(w=>w.id===command.windowId); if(!w)throw Error('النافذة غير موجودة.'); if(w.locked)throw Error('النافذة مثبتة.'); r.windows=r.windows.filter(x=>x.id!==w.id); }
    if (command.type === 'notch') {
        if(r.footprint) throw Error('المساحة غير مستطيلة أصلًا؛ حرر حدودها بدل إضافة تجويف ثانٍ تلقائيًا.'); const nw=Number(command.width),nd=Number(command.depth),corner=command.corner;
        if(!finite(nw)||!finite(nd)||nw<=0||nd<=0||nw>=r.w-.5||nd>=r.d-.5||!['ne','nw','se','sw'].includes(corner)) throw Error('أبعاد أو زاوية التجويف غير صالحة.');
        const x=r.x,y=r.y,X=r.x+r.w,Y=r.y+r.d;
        const poly=corner==='ne'?[[x,y],[X,y],[X,Y-nd],[X-nw,Y-nd],[X-nw,Y],[x,Y]]:corner==='nw'?[[x,y],[X,y],[X,Y],[x+nw,Y],[x+nw,Y-nd],[x,Y-nd]]:corner==='sw'?[[x,y+nd],[x+nw,y+nd],[x+nw,y],[X,y],[X,Y],[x,Y]]:[[x,y],[X-nw,y],[X-nw,y+nd],[X,y+nd],[X,Y],[x,Y]];
        r.footprint=poly.map(p=>p.map(round));
    }
    const swapGeometry = target => { if (!target || target.id === r.id) throw Error('اختر غرفة ثانية للمبادلة.'); if(r.footprint||target.footprint) throw Error('المبادلة التلقائية لا تغيّر هندسة مساحة غير مستطيلة.'); if (!candidate.levels.some(l => l.rooms.includes(r) && l.rooms.includes(target))) throw Error('المبادلة متاحة داخل الدور نفسه فقط.'); const ra = { x:r.x,y:r.y,w:r.w,d:r.d,doors:clone(r.doors),windows:clone(r.windows||[]) }, ta = { x:target.x,y:target.y,w:target.w,d:target.d,doors:clone(target.doors),windows:clone(target.windows||[]) }; Object.assign(r, ta, { doors: ta.doors.map((d,i)=>({ ...d,id:`${r.id}-door-${i}` })), windows:ta.windows.map((w,i)=>({...w,id:`${r.id}-window-${i+1}`})) }); Object.assign(target, ra, { doors: ra.doors.map((d,i)=>({ ...d,id:`${target.id}-door-${i}` })), windows:ra.windows.map((w,i)=>({...w,id:`${target.id}-window-${i+1}`})) }); };
    if (command.type === 'swap') swapGeometry(rooms.find(s => s.id === command.targetId));
    if (command.type === 'near') {
        const level = candidate.levels.find(l => l.rooms.includes(r)), free = level.rooms.filter(x => x.id !== r.id && !x.locked && !['hall','stairs','elevator'].includes(x.kind)); let target;
        if (command.target === 'entry') target = [...free].sort((a,b)=>distanceToEntry(candidate,a)-distanceToEntry(candidate,b))[0];
        else if (command.target === 'garden') target = [...free].sort((a,b)=>Number(touchesGardenEdge(candidate,b))-Number(touchesGardenEdge(candidate,a)))[0];
        else if (command.targetId) target = free.find(x=>x.id===command.targetId);
        if (!target) throw Error('لم أجد موضعًا مناسبًا غير مثبت لتنفيذ علاقة القرب.'); swapGeometry(target);
    }
    checkLocks(model, candidate);
    const issues = validate(candidate), blockers = issues.filter(i => i.status === 'error');
    return { candidate, changes: diffModels(model, candidate), issues, blockers, impact: impactSummary(model, candidate), base: JSON.stringify(model), command };
}
/**
 * Turn a blocked geometry preview into a second, explicit proposal when a
 * conservative deterministic solution exists. Locked geometry is never moved.
 * The solver first tries to transfer the conflicting strip from an adjacent,
 * unlocked room so the requested room keeps its requested size. Only if that
 * is impossible does it consider trimming the changed room. It returns null
 * rather than guessing when it cannot produce a zero-error model.
 */
export function resolvePreview(model, preview) {
    assertModel(model);
    if (!preview || preview.base !== JSON.stringify(model)) throw Error('تغيّر المشروع بعد المعاينة؛ أنشئ معاينة جديدة.');
    const requested = clone(preview.candidate), candidate = clone(preview.candidate), changed = new Set(preview.changes.map(c => c.id));
    const notes = [];
    const roomById = (m, id) => m.levels.flatMap(l => l.rooms).find(r => r.id === id);
    const levelOf = (m,id) => m.levels.find(l=>l.rooms.some(r=>r.id===id));
    const errorCount = m => validate(m).filter(i => i.status === 'error').length;
    const geometryKey = r => `${round(r.x)}|${round(r.y)}|${round(r.w)}|${round(r.d)}`;
    if ([...changed].some(id=>roomById(candidate,id)?.footprint)) return null;
    const overlapSpan = (a1,a2,b1,b2) => Math.min(a2,b2)-Math.max(a1,b1);
    const clampBounds = (m, id) => {
        const r = roomById(m, id); if (!r || r.locked || !changed.has(id)) return false;
        const before = geometryKey(r);
        r.w = round(Math.min(r.w, m.site.width)); r.d = round(Math.min(r.d, m.site.depth));
        r.x = round(Math.max(0, Math.min(r.x, m.site.width - r.w)));
        r.y = round(Math.max(0, Math.min(r.y, m.site.depth - r.d)));
        return geometryKey(r) !== before;
    };
    const scoreOption = (t, victimId, donorId=null, kind='trim') => {
        const r=roomById(t,victimId), req=roomById(requested,victimId); if(!r||!req) return null;
        try { checkLocks(model,t); assertModel(t); } catch { return null; }
        const errors=errorCount(t), reqArea=req.w*req.d, keepArea=r.w*r.d;
        const drift=Math.abs(r.x-req.x)+Math.abs(r.y-req.y)+Math.abs(r.w-req.w)+Math.abs(r.d-req.d);
        return {t,errors,loss:Math.max(0,reqArea-keepArea),drift,donorId,kind};
    };
    for (let pass = 0; pass < 20; pass++) {
        const blockers = validate(candidate).filter(i => i.status === 'error');
        if (!blockers.length) {
            checkLocks(model, candidate); assertModel(candidate);
            const issues = validate(candidate);
            return { candidate, changes: diffModels(model, candidate), issues, blockers: [], impact: impactSummary(model, candidate), base: JSON.stringify(model), command: preview.command, autoResolved: true, resolutionNotes: notes };
        }
        let progressed = false;
        const bounds = blockers.find(i => i.id.startsWith('bounds-') && i.targets.some(id => changed.has(id)));
        if (bounds) {
            const id = bounds.targets.find(id => changed.has(id));
            if (clampBounds(candidate, id)) { notes.push(`أُعيد ${roomById(candidate,id)?.name || 'العنصر'} داخل حدود الأرض مع الحفاظ على أكبر أبعاد ممكنة.`); progressed = true; }
        }
        if (progressed) continue;
        const ov = blockers.find(i => i.id.startsWith('overlap-') && i.targets.some(id => changed.has(id)));
        if (!ov) return null;
        const ids = ov.targets, editableIds = ids.filter(id => { const r=roomById(candidate,id); return changed.has(id) && r && !r.locked; });
        if (!editableIds.length) return null;
        const victimId = editableIds[0], obstacleId = ids.find(id => id !== victimId), v = roomById(candidate,victimId), o = roomById(candidate,obstacleId), baseV=roomById(model,victimId);
        if (!v || !o || !baseV) return null;
        const requestedRoom = roomById(requested, victimId) || v, options = [], level=levelOf(candidate,victimId), baseLevel=levelOf(model,victimId);
        const addOption = (t, donorId=null, kind='trim') => { const scored=scoreOption(t,victimId,donorId,kind); if(scored) options.push(scored); };

        // 1) Space transfer: preserve the requested room dimensions by borrowing
        // exactly the conflicting strip from the unlocked room on the opposite side.
        const xOverlap=overlapSpan(v.x,v.x+v.w,o.x,o.x+o.w), yOverlap=overlapSpan(v.y,v.y+v.d,o.y,o.y+o.d), tol=.02;
        if (xOverlap > .002 && yOverlap > .002 && level && baseLevel) {
            const transfer = (side, amount) => {
                if (!(amount > .002)) return;
                const baseCandidates=baseLevel.rooms.filter(d=>d.id!==victimId&&d.id!==obstacleId&&!d.locked&&!changed.has(d.id));
                let donor;
                if(side==='south') donor=baseCandidates.filter(d=>Math.abs(d.y+d.d-baseV.y)<=tol && overlapSpan(d.x,d.x+d.w,baseV.x,baseV.x+baseV.w)>.5).sort((a,b)=>overlapSpan(b.x,b.x+b.w,baseV.x,baseV.x+baseV.w)-overlapSpan(a.x,a.x+a.w,baseV.x,baseV.x+baseV.w))[0];
                if(side==='north') donor=baseCandidates.filter(d=>Math.abs(d.y-(baseV.y+baseV.d))<=tol && overlapSpan(d.x,d.x+d.w,baseV.x,baseV.x+baseV.w)>.5).sort((a,b)=>overlapSpan(b.x,b.x+b.w,baseV.x,baseV.x+baseV.w)-overlapSpan(a.x,a.x+a.w,baseV.x,baseV.x+baseV.w))[0];
                if(side==='west') donor=baseCandidates.filter(d=>Math.abs(d.x+d.w-baseV.x)<=tol && overlapSpan(d.y,d.y+d.d,baseV.y,baseV.y+baseV.d)>.5).sort((a,b)=>overlapSpan(b.y,b.y+b.d,baseV.y,baseV.y+baseV.d)-overlapSpan(a.y,a.y+a.d,baseV.y,baseV.y+baseV.d))[0];
                if(side==='east') donor=baseCandidates.filter(d=>Math.abs(d.x-(baseV.x+baseV.w))<=tol && overlapSpan(d.y,d.y+d.d,baseV.y,baseV.y+baseV.d)>.5).sort((a,b)=>overlapSpan(b.y,b.y+b.d,baseV.y,baseV.y+baseV.d)-overlapSpan(a.y,a.y+a.d,baseV.y,baseV.y+baseV.d))[0];
                if(!donor) return;
                const t=clone(candidate), rv=roomById(t,victimId), rd=roomById(t,donor.id); if(!rv||!rd) return;
                if(side==='south'){ if(rd.d-amount<1) return; rd.d=round(rd.d-amount); rv.y=round(rv.y-amount); }
                if(side==='north'){ if(rd.d-amount<1) return; rd.y=round(rd.y+amount); rd.d=round(rd.d-amount); rv.y=round(rv.y+amount); }
                if(side==='west'){ if(rd.w-amount<1) return; rd.w=round(rd.w-amount); rv.x=round(rv.x-amount); }
                if(side==='east'){ if(rd.w-amount<1) return; rd.x=round(rd.x+amount); rd.w=round(rd.w-amount); rv.x=round(rv.x+amount); }
                addOption(t,donor.id,'transfer');
            };
            if (v.y < o.y && v.y+v.d > o.y) transfer('south', round(v.y+v.d-o.y));
            if (v.y < o.y+o.d && v.y+v.d > o.y+o.d) transfer('north', round(o.y+o.d-v.y));
            if (v.x < o.x && v.x+v.w > o.x) transfer('west', round(v.x+v.w-o.x));
            if (v.x < o.x+o.w && v.x+v.w > o.x+o.w) transfer('east', round(o.x+o.w-v.x));
        }

        // 2) Conservative trim fallback. It may reduce the requested gain, but
        // never moves locked neighbours and is only offered if the model validates.
        const pushTrim = patch => {
            const t=clone(candidate), r=roomById(t,victimId); Object.assign(r,patch);
            r.x=round(r.x);r.y=round(r.y);r.w=round(r.w);r.d=round(r.d);
            if(r.w<1||r.d<1||r.x<0||r.y<0||r.x+r.w>t.site.width+.002||r.y+r.d>t.site.depth+.002) return;
            addOption(t,null,'trim');
        };
        const vRight=v.x+v.w, vTop=v.y+v.d, oRight=o.x+o.w, oTop=o.y+o.d;
        if (v.x < o.x) pushTrim({ w:o.x-v.x });
        if (vRight > oRight) pushTrim({ x:oRight, w:vRight-oRight });
        if (v.y < o.y) pushTrim({ d:o.y-v.y });
        if (vTop > oTop) pushTrim({ y:oTop, d:vTop-oTop });
        if (!options.length) return null;
        options.sort((a,b)=>a.errors-b.errors || (a.kind==='transfer'?-1:0)-(b.kind==='transfer'?-1:0) || a.loss-b.loss || a.drift-b.drift);
        const best=options[0];
        if (best.errors >= blockers.length) return null;
        const beforeArea=round(v.w*v.d), afterRoom=roomById(best.t,victimId), afterArea=round(afterRoom.w*afterRoom.d);
        candidate.levels = best.t.levels;
        if(best.kind==='transfer' && best.donorId){
            const donorBefore=roomById(candidate,best.donorId), donorBase=roomById(model,best.donorId), transferred=round(Math.abs((donorBase?.w*donorBase?.d||0)-(donorBefore?.w*donorBefore?.d||0)));
            notes.push(`حُفظ ${o.locked ? 'العنصر المثبّت ' : ''}${o.name} دون تحريك، ونُقلت ${transferred} م² تقريبًا من ${donorBefore?.name || 'مساحة مجاورة'} إلى ${afterRoom.name} لإزالة التداخل مع إبقاء أبعاد الطلب الجديد.`);
        } else {
            notes.push(`حُفظ ${o.locked ? 'العنصر المثبّت ' : ''}${o.name} دون تحريك، وعُدّلت حدود ${afterRoom.name} لإزالة التداخل (${beforeArea} → ${afterArea} م² في المعاينة).`);
        }
    }
    return null;
}

export function commitPreview(model, preview) { if (preview.base !== JSON.stringify(model))
    throw Error('تغيّر المشروع بعد المعاينة؛ أنشئ معاينة جديدة.'); if (validate(preview.candidate).some(i => i.status === 'error'))
    throw Error('لا يمكن اعتماد تعديل به تعارض هندسي.'); checkLocks(model, preview.candidate); assertModel(preview.candidate); return clone(preview.candidate); }
/** Deterministic, openly-labelled Arabic command parser. Never silently treats unknown prose as success. */
export function parseCommand(text, model, selectedId) {
    const t = normalizeText(text), rooms = model.levels.flatMap(l => l.rooms); let roomId = selectedId;
    const explicit = rooms.filter(r => t.includes(normalizeText(r.name))); if (explicit.length === 1) roomId = explicit[0].id;
    const aliases = [['majlis', /(?:المجلس|مجلس)/], ['kitchen', /(?:المطبخ|مطبخ)/], ['living', /(?:المعيشه|معيشه|الصاله|صاله)/], ['bedroom', /(?:غرفه النوم|غرف نوم)/], ['office', /(?:المكتب|مكتب)/]];
    for (const [kind,re] of aliases) if (re.test(t)) { const ms=rooms.filter(r=>r.kind===kind); if (ms.length===1) roomId=ms[0].id; }
    const r = rooms.find(r => r.id === roomId); if (!r) throw Error('حدّد غرفة من المخطط أولًا، ثم اكتب تعديلها.');
    const name = text.match(/(?:سمّ|سمي|سم|اسمها|غيّر الاسم إلى|غير الاسم الى)\s+(.+)/); if (name) return { type:'rename',roomId,name:name[1].trim() };
    const nearEntry = /(?:انقل|حرك|خلي|اجعل)?[^،.]{0,55}(?:قريب|قرب)\s*(?:من\s*)?(?:المدخل|مدخل)/.test(t); if (nearEntry) return { type:'near',roomId,target:'entry' };
    const nearGarden = /(?:انقل|حرك|خلي|اجعل)?[^،.]{0,55}(?:قريب|قرب)\s*(?:من\s*)?(?:الحديقه|حديقه|الخارج|المسبح)/.test(t); if (nearGarden) return { type:'near',roomId,target:'garden' };
    const nearRoom = t.match(/(?:قريب|قرب)\s*(?:من\s*)?(.+)$/); if (nearRoom) { const q=nearRoom[1].trim(), ms=rooms.filter(x=>x.id!==roomId && normalizeText(x.name).includes(q)); if (ms.length===1) return { type:'near',roomId,targetId:ms[0].id }; }
    const token=String.raw`(\d+(?:\.\d+)?|واحد|واحده|اثنين|اثنان|ثلاثه?|اربعه?|خمسه?)`; const ex=t.match(new RegExp(String.raw`(?:وسع|كبر|زيد)[^\d]{0,22}${token}?\s*(?:متر|م)?[^،.]{0,20}(?:باتجاه|نحو|جهة|جهه)?\s*(شرق|غرب|شمال|جنوب|الحديقه|حديقه|الشارع)`));
    if (ex) { const n = ex[1] ? (/^\d/.test(ex[1]) ? Number(ex[1]) : wordNumbers[ex[1]]) : 1, d=ex[2]; return { type:'expand',roomId,amount:n||1,direction:d.includes('حديق')?'garden':d==='الشارع'?'street':{شرق:'east',غرب:'west',شمال:'north',جنوب:'south'}[d] }; }
    if (/(?:وسعها|كبرها|وسع|كبر)\s*(?:متر|1\s*متر)?/.test(t) && /حديق/.test(t)) return { type:'expand',roomId,amount:1,direction:'garden' };
    const dimensions = t.match(/(?:ابعاد|مقاس|خليها|اجعلها)\s*(\d+(?:\.\d+)?)\s*(?:×|x|في|\*)\s*(\d+(?:\.\d+)?)/); if (dimensions) return { type:'resize',roomId,w:+dimensions[1],d:+dimensions[2] };
    const width = t.match(/(?:عرضها|العرض|عرض)\s*(?:الي|الى|=)?\s*(\d+(?:\.\d+)?)/); if (width) return { type:'resize',roomId,w:+width[1] };
    const depth = t.match(/(?:عمقها|العمق|عمق|طولها|الطول)\s*(?:الي|الى|=)?\s*(\d+(?:\.\d+)?)/); if (depth) return { type:'resize',roomId,d:+depth[1] };
    const move = t.match(/(?:انقل|حرك)[^\d]{0,30}(\d+(?:\.\d+)?)\s*(?:متر|م)?\s*(?:باتجاه|نحو|الي|الى)?\s*(شرق|غرب|شمال|جنوب)/); if (move) { const n=+move[1]; return { type:'move',roomId,x:r.x+(move[2]==='شرق'?n:move[2]==='غرب'?-n:0),y:r.y+(move[2]==='شمال'?n:move[2]==='جنوب'?-n:0) }; }
    const door = t.match(/(?:الباب|باب).*(شرق|غرب|شمال|جنوب)/); if (door) return { type:'door',roomId,side:{شرق:'east',غرب:'west',شمال:'north',جنوب:'south'}[door[1]],entry:r.doors[0]?.entry||false };
    const win=t.match(/(?:نافذه|شباك)[^،.]{0,30}(شرق|غرب|شمال|جنوب)(?:[^\d]{0,18}(\d+(?:\.\d+)?)\s*(?:متر|م))?/); if(win) return {type:'window',roomId,side:{شرق:'east',غرب:'west',شمال:'north',جنوب:'south'}[win[1]],...(win[2]?{width:Number(win[2])}:{})};
    const notch=t.match(/(?:تجويف|نقره|قص)[^\d]{0,18}(\d+(?:\.\d+)?)\s*(?:×|x|في|\*)\s*(\d+(?:\.\d+)?)[^،.]{0,30}(شمال\s*شرق|شمال\s*غرب|جنوب\s*شرق|جنوب\s*غرب)/); if(notch){const c=notch[3].replace(/\s+/g,' '),corner={'شمال شرق':'ne','شمال غرب':'nw','جنوب شرق':'se','جنوب غرب':'sw'}[c];return{type:'notch',roomId,width:Number(notch[1]),depth:Number(notch[2]),corner};}
    const swap = t.match(/(?:بادل|بدل|بدّل).*?(?:مع)\s*(.+)/); if (swap) { const ms=rooms.filter(s=>normalizeText(s.name)===swap[1].trim()); if (ms.length!==1) throw Error('اسم الغرفة الثانية غير واضح أو مكرر؛ استخدم قائمة المبادلة.'); return { type:'swap',roomId,targetId:ms[0].id }; }
    throw Error('الأمر غير واضح للمحلل المحلي. أمثلة: «انقل المجلس قرب المدخل»، «وسعها متر باتجاه الحديقة»، «العرض 5»، «أبعاد 5×4»، «انقل 1 متر شمال»، «الباب جنوب»، «نافذة شمال 1.5 متر»، «تجويف 1×1 شمال شرق».');
}
export function createHistory(m) { return { schemaVersion: VERSION, projectId: m.id, revisions: [{ id: uid(), label: 'البداية', at: new Date().toISOString(), model: clone(m), parentIndex: null }], cursor: 0, audit: [{ type: 'create', at: new Date().toISOString() }] }; }
export function current(h) { return h.revisions[h.cursor].model; }
export function pushHistory(h, m, label) { assertModel(m); if (m.id !== h.projectId)
    throw Error('هوية المشروع غير متطابقة.'); const next = clone(h); next.revisions.push({ id: uid(), label: String(label).slice(0, 120), at: new Date().toISOString(), model: clone(m), parentIndex: h.cursor }); next.cursor = next.revisions.length - 1; next.audit.push({ type: 'edit', at: new Date().toISOString(), revisionId: next.revisions[next.cursor].id }); return next; }
export function assertHistory(h) { if (!h || h.schemaVersion !== VERSION || !Array.isArray(h.revisions) || h.revisions.length < 1 || h.revisions.length > 100 || !Number.isInteger(h.cursor) || h.cursor < 0 || h.cursor >= h.revisions.length || !Array.isArray(h.audit) || h.audit.length > 2000)
    throw Error('سجل النسخ غير صالح (الحد 100 نسخة).'); const revisionIds = new Set(); for (const [index, r] of h.revisions.entries()) {
    if (revisionIds.has(r.id) || r.parentIndex !== undefined && r.parentIndex !== null && (!Number.isInteger(r.parentIndex) || r.parentIndex < 0 || r.parentIndex >= index))
        throw Error('رابط النسخة السابقة غير صالح.');
    revisionIds.add(r.id);
    if (!safeString(r.id, 100) || !safeString(r.label, 120) || !safeString(r.at, 80))
        throw Error('نسخة غير صالحة.');
    assertModel(r.model);
    if (r.model.id !== h.projectId)
        throw Error('هوية المشروع غير متطابقة.');
} return h; }
export function exportEnvelope(h) { return { format: 'masar-project', version: VERSION, exportedAt: new Date().toISOString(), disclaimer: 'تصميم مفاهيمي، لا يصلح للبناء دون مراجعة واعتماد المختصين. جميع الأبعاد بالمتر.', history: clone(h) }; }
export function importEnvelope(text) { if (text.length > 8000000)
    throw Error('الملف يتجاوز 8 ميجابايت.'); const d = JSON.parse(text); if (d?.format !== 'masar-project' || d.version !== VERSION)
    throw Error('هذا ليس ملف مشروع مسار.'); return assertHistory(d.history); }
export function parseDXF(text, scale = 1) { if (text.length > 2000000)
    throw Error('ملف DXF يتجاوز 2 ميجابايت.'); const raw = text.replace(/\r/g, '').split('\n'); const pairs = []; for (let i = 0; i + 1 < raw.length; i += 2)
    pairs.push([raw[i].trim(), raw[i + 1].trim()]); const lines = []; let entity = null, points = [], v = {}; const flush = () => { if (entity === 'LINE' && [v.x, v.y, v.x2, v.y2].every(finite))
    lines.push([v.x, v.y, v.x2, v.y2]); if (entity === 'LWPOLYLINE') {
    for (let i = 1; i < points.length; i++)
        if (points[i - 1].every(finite) && points[i].every(finite))
            lines.push([...points[i - 1], ...points[i]]);
    if (v.closed && points.length > 2)
        lines.push([...points.at(-1), ...points[0]]);
} v = {}; points = []; }; for (const [code, value] of pairs) {
    if (code === '0') {
        flush();
        entity = value;
    }
    else if (entity === 'LINE') {
        const k = { '10': 'x', '20': 'y', '11': 'x2', '21': 'y2' }[code];
        if (k)
            v[k] = Number(value);
    }
    else if (entity === 'LWPOLYLINE') {
        if (code === '10')
            points.push([Number(value), NaN]);
        if (code === '20' && points.length)
            points.at(-1)[1] = Number(value);
        if (code === '70')
            v.closed = !!(Number(value) & 1);
    }
} flush(); if (!lines.length)
    throw Error('لم تُعثر على LINE أو LWPOLYLINE ثنائية الأبعاد. DWG وIFC غير مدعومين في هذا المستورد.'); if (lines.length > 3000)
    throw Error('الرسم يتجاوز 3000 خط.'); if (!finite(scale) || scale <= 0 || scale > 1000)
    throw Error('مقياس الرسم غير صالح.'); const clean = lines.map(l => l.map(v => round(v * scale))); if (clean.some(l => l.some(v => !finite(v) || Math.abs(v) > 1e7)))
    throw Error('إحداثيات الرسم غير صالحة.'); return clean; }
export function exportDXF(m, levelId) { const l = m.levels.find(l => l.id === levelId) || m.levels[0]; let out = '0\nSECTION\n2\nHEADER\n9\n$INSUNITS\n70\n6\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n'; for (const r of l.rooms) {
    const points = roomPolygon(r);
    out += `0\nLWPOLYLINE\n8\n${r.kind}\n90\n${points.length}\n70\n1\n`;
    for (const [x, y] of points)
        out += `10\n${round(x)}\n20\n${round(y)}\n`;
} return out + '0\nENDSEC\n0\nEOF\n'; }
