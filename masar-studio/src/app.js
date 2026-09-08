import { openRenderStudio } from './render-ui.js';
import { KINDS, COLORS, clone, uid, round, understand, briefIssues, generate, assertModel, validate, totals, area, propose, resolvePreview, commitPreview, parseCommand, checkLocks, diffModels, createHistory, current, pushHistory, assertHistory, exportEnvelope, importEnvelope, parseDXF, exportDXF, designMetrics, createAlternatives, impactSummary, requirementStatus, distanceToEntry, touchesGardenEdge } from '../shared/model.js';
import { escapeHTML as E, planSVG, exportOBJ } from '../shared/geometry.js';
import { deriveBuildingGraph, elementScheduleCSV, requirementMatrix, requirementMatrixCSV, evaluateRulePack, exportIFC, projectReadiness, csvCell } from '../shared/building.js';
import { parseIFC } from '../shared/ifc.js';
import { effectiveAuthoring } from '../shared/authoring.js';
import { StudioRenderer } from './renderer.js';
import { saveLocal, listLocal, loadLocal, loadLocalVersions, deleteLocal, Api } from './storage.js';
const iconPaths = { folder: 'M3 6h7l2 2h9v11H3z', history: 'M3 11a9 9 0 1 1 2 7M3 5v6h6M12 7v5l3 2', share: 'M15 8 9 11m0 2 6 3M19 5a2 2 0 1 1-4 0 2 2 0 0 1 4 0ZM9 12a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm10 7a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z', download: 'M12 3v12m-5-5 5 5 5-5M4 16v4h16v-4', plus: 'M12 5v14M5 12h14', layers: 'm12 3 10 5-10 5L2 8zm-10 9 10 5 10-5M2 16l10 5 10-5', cube: 'm3 6 9-4 9 4v12l-9 4-9-4Zm0 0 9 5 9-5M12 11v11', split: 'M3 4h18v16H3ZM12 4v16', undo: 'M8 4 3 9l5 5M3 9h11a6 6 0 0 1 0 12', redo: 'm16 4 5 5-5 5M21 9H10a6 6 0 0 0 0 12', fit: 'M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5', ruler: 'm3 16 13-13 5 5L8 21Zm4-4 2 2m2-6 2 2m2-6 2 2', sofa: 'M5 11V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v4M3 10h3v5h12v-5h3v9H3ZM5 19v2m14-2v2', rotate: 'M5 8a8 8 0 0 1 14-2l2 3m0-5v5h-5M19 16a8 8 0 0 1-14 2l-2-3m0 5v-5h5', link: 'm8 16 8-8M9 5l2-2a5 5 0 0 1 7 7l-2 2M8 12l-2 2a5 5 0 0 0 7 7l2-2', sparkles: 'm12 2 2.6 7.4L22 12l-7.4 2.6L12 22l-2.6-7.4L2 12l7.4-2.6ZM20 1v5m-2.5-2.5h5', shield: 'm12 2 8 4v6c0 6-8 10-8 10S4 18 4 12V6Zm-4 10 3 3 5-6', arrow: 'M19 12H5m7-7-7 7 7 7', close: 'm6 6 12 12M6 18 18 6', lock: 'M6 11h12v10H6ZM8 11V6a4 4 0 0 1 8 0v5m-4 4v3', unlock: 'M6 11h12v10H6ZM8 11V6a4 4 0 0 1 8 0m-4 9v3', chevron: 'm8 5 7 7-7 7', check: 'm4 12 5 5L20 6', alert: 'm12 3 10 18H2Zm0 6v5m0 3v.2', sliders: 'M5 3v5m0 4v9M12 3v11m0 4v3m7-18v3m0 4v11M2 8h6M9 14h6M16 6h6', variants: 'M3 3h7v7H3Zm11 0h7v7h-7ZM3 14h7v7H3Zm11 0h7v7h-7Z', trash: 'M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7', upload: 'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6', file: 'M5 2h9l5 5v15H5Zm9 0v5h5M9 12h6m-6 4h6', message: 'M3 4h18v13H9l-6 4Z', home: 'm2 11 10-9 10 9M5 9v13h14V9M10 22v-7h4v7', image: 'M3 3h18v18H3Zm0 13 6-6 5 5 3-3 4 4M16 7h.01', cloud: 'M6 18a5 5 0 1 1 1-10 6 6 0 0 1 11 2 4 4 0 0 1 0 8Z', door: 'M5 22V2h14v20M5 2l10 3v17M11 12v1' };
const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${iconPaths[name] || iconPaths.cube}"/></svg>`;
function icons(root = document) { root.querySelectorAll('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); el.removeAttribute('data-icon'); }); }
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)], fmt = n => Number(n).toLocaleString('en-US', { maximumFractionDigits: 1 });
const api = new Api();
const state = { history: null, selectedId: null, levelId: 'l0', view: window.innerWidth < 720 ? '2d' : 'split', dimensions: true, furniture: true, all: false, cutaway: true, preview: null, demo: true, readOnly: false, dirty: false, saveError: null, undoStack: [], versions: new Map(), ai: false, pendingBrief: null, alternatives: [], authMode: 'login', imageRef: null, shareToken: null, measurement: { active: false, a: null, b: null }, ifcCandidate: null };
let renderer = null, saveQueue = Promise.resolve(), drag = null, ignoreClickUntil = 0, lastFocus = null, toastNumber = 0;
const model = () => current(state.history), shown = () => state.preview?.candidate || model(), selected = () => shown().levels.flatMap(l => l.rooms).find(r => r.id === state.selectedId);
function toast(message, error = false) { const existing = [...document.querySelectorAll('.toast')].find(x => x.dataset.message === message); if (existing)
    return; while (document.querySelectorAll('.toast').length >= 3)
    document.querySelector('.toast').remove(); const el = document.createElement('div'); el.dataset.message = message; el.className = 'toast' + (error ? ' error' : ''); el.id = `toast-${++toastNumber}`; el.innerHTML = `<button data-action="dismiss-toast" aria-label="إغلاق الإشعار">×</button>${E(message)}`; $('#toasts').append(el); setTimeout(() => el.remove(), error ? 14000 : 6500); }
function reportError(e) {
    const message=e.message||'تعذّرت العملية؛ لم نطبق تغييرًا.';console.warn('[MASAR]',message);
    if($('#modal').open){
        let box=$('#modal-error');if(!box){box=document.createElement('div');box.id='modal-error';box.className='notice error';box.setAttribute('role','alert');box.tabIndex=-1;$('#modal-content').prepend(box);}
        box.textContent=message;box.scrollIntoView({block:'nearest'});box.focus({preventScroll:true});
    } else toast(message,true);
}
function showModal(title, html, kicker = 'MASAR STUDIO') { lastFocus = document.activeElement; $('#modal-title').textContent = title; $('#modal-content').innerHTML = html; $('#modal-kicker').textContent = kicker; icons($('#modal')); if (!$('#modal').open)
    $('#modal').showModal(); }
function closeModal() { $('#modal').close(); lastFocus?.focus?.(); }
function mutable() { if (state.readOnly)
    throw Error('هذا رابط مراجعة للقراءة فقط.'); if (state.preview)
    throw Error('اعتمد المعاينة الحالية أو ألغها قبل إجراء تعديل آخر.'); }
function saveStatus(text) { $('#save-status').textContent = text; }
function persist() { if (state.readOnly)
    return Promise.resolve(); const snapshot = clone(state.history); state.dirty = true; state.saveError = null; saveStatus('جارٍ الحفظ على هذا الجهاز…'); saveQueue = saveQueue.catch(() => { }).then(() => saveLocal(snapshot,Object.fromEntries([...state.versions].filter(([key])=>key.endsWith(':'+snapshot.projectId))))).then(() => { if (JSON.stringify(state.history) === JSON.stringify(snapshot)) {
    state.dirty = false;
    saveStatus('محفوظ على هذا الجهاز · ليس نسخة سحابية');
} }).catch(e => { state.saveError = e.message; state.dirty = true; saveStatus('لم يكتمل الحفظ · نزّل نسخة احتياطية'); reportError(e); }); return saveQueue; }
function edit(next, label) { mutable(); if (state.history.revisions.length >= 100)
    throw Error('بلغ المشروع 100 نسخة. صدّره ثم أنشئ نسخة مستقلة لمتابعة العمل دون حذف التاريخ.'); state.history = pushHistory(state.history, next, label); state.undoStack = []; state.demo = false; render(); persist(); }
function selectRoom(id) { const level = shown().levels.find(l => l.rooms.some(r => r.id === id)); if (!level)
    return; state.selectedId = id; state.levelId = level.id; render(); }
function stage(command, label = 'تعديل المساحة') {
    if (state.readOnly)
        throw Error('رابط المراجعة لا يسمح بالتعديل.');
    if (state.preview)
        throw Error('ألغِ المعاينة الحالية قبل طلب تعديل آخر.');
    state.preview = { ...propose(model(), command), label };
    if (!state.preview.changes.length) {
        state.preview = null;
        toast('لم تتغيّر أي قيمة.');
        return;
    }
    render();
    $('#assistant-message').textContent = 'المعاينة لا تغيّر النسخة المحفوظة. افحص العناصر المتأثرة ثم اعتمد أو ألغِ.';
}
function render() {
    if (!state.history)
        return;
    const m = shown(), base = model(), r = selected(), issues = validate(m), t = totals(m), dm = designMetrics(m);
    $('#project-title').textContent = base.title;
    $('#brief-name').textContent = base.title;
    $('#project-type').textContent = state.readOnly ? 'رابط مراجعة · للقراءة فقط' : ({villa:'فيلا',chalet:'شاليه',office:'مكاتب',warehouse:'مستودع',retail:'تجاري'}[base.design?.projectType || 'villa'] || 'تصميم') + ' · ' + ({concept:'فكرة',development:'تطوير',review:'مراجعة'}[base.design?.stage || 'concept']);
    $('#demo-badge').hidden = !state.demo;
    $('#account-button').textContent = api.user?.name?.slice(0, 1) || 'م';
    $$('.design-stage button').forEach(b => { const active=b.dataset.stage === (base.design?.stage || 'concept'); b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active)); b.disabled=state.readOnly; });
    const primaryCount = ['villa','chalet'].includes(m.design?.projectType || 'villa') ? `${t.bedrooms.toString().padStart(2,'0')} غرف نوم` : m.design?.projectType === 'office' ? `${t.offices.toString().padStart(2,'0')} مكاتب` : `${t.rooms} مساحات`;
    $('#brief-content').innerHTML = `<div class="brief-grid"><div class="brief-stat"><span>مساحة الأرض</span><strong>${fmt(t.landArea)}</strong><small>م²</small></div><div class="brief-stat"><span>الأدوار إجمالًا</span><strong>${m.levels.length.toString().padStart(2, '0')}</strong><small>أدوار</small></div><div class="brief-stat"><span>أبعاد الأرض</span><strong>${fmt(m.site.width)} × ${fmt(m.site.depth)}</strong></div><div class="brief-stat"><span>البرنامج</span><strong class="brief-text-value">${E(primaryCount)}</strong></div></div><div class="design-score-mini"><span>مؤشر المفهوم</span><strong>${fmt(dm.overall)}</strong><small>/100 · للمقارنة فقط</small></div><div class="req-list">${m.requirements.slice(0, 6).map(req => { const rs=requirementStatus(m,req), stateLabel=rs.measurable ? (rs.satisfied ? 'محقق' : 'يحتاج تحسين') : (req.source==='assumed'?'افتراض':'طلبك'); return `<div class="req-item"><button class="req-icon" data-action="toggle-requirement" data-id="${E(req.id)}" aria-label="${req.locked ? 'إلغاء تثبيت' : 'تثبيت'} ${E(req.label)}" ${state.readOnly ? 'disabled' : ''}>${icon(req.locked ? 'lock' : 'unlock')}</button><span>${E(req.label)}</span><span class="source-tag ${rs.measurable && !rs.satisfied ? 'warn' : req.source === 'assumed' ? 'assumed' : ''}">${stateLabel}</span></div>`; }).join('')}<div class="req-item"><span class="req-icon">${icon('home')}</span><span>جهة الشارع: ${E(m.site.street)}</span><span class="source-tag ${m.brief.sources?.street === 'assumed' ? 'assumed' : ''}">${m.brief.sources?.street === 'assumed' ? 'افتراض' : 'طلبك'}</span></div></div><div class="brief-links"><button class="description-link text-button" data-action="brief">${icon('file')} الطلب الكامل</button><button class="description-link text-button green" data-action="design-settings">${icon('sliders')} إعدادات التصميم</button></div>`;
    $('#level-tree').innerHTML = m.levels.map(l => `<div class="tree-level"><button class="tree-level-label" data-action="level" data-id="${E(l.id)}">${icon('layers')}${E(l.name)}<span class="count">${l.rooms.length} عناصر</span></button>${l.id === state.levelId ? `<div class="tree-rooms">${l.rooms.map(room => `<button class="tree-room ${room.id === state.selectedId ? 'selected' : ''}" data-action="select" data-id="${E(room.id)}" aria-pressed="${room.id === state.selectedId}"><span class="room-color" style="background:${COLORS[room.kind]}"></span>${E(room.name)}<span class="room-area">${fmt(area(room))} م²</span>${room.locked ? icon('lock') : ''}</button>`).join('')}</div>` : ''}</div>`).join('');
    const level = m.levels.find(l => l.id === state.levelId) || m.levels[0];
    state.levelId = level.id;
    $('#level-label').textContent = level.name;
    $('#floor-tabs').innerHTML = m.levels.map(l => `<button data-action="level" data-id="${E(l.id)}" class="${l.id === level.id ? 'active' : ''}" aria-pressed="${l.id === level.id}">${E(l.name)}</button>`).join('');
    $('#view-deck').dataset.view = state.view;
    $$('[data-action="view"]').forEach(b => { b.classList.toggle('active', b.dataset.view === state.view); b.setAttribute('aria-pressed', String(b.dataset.view === state.view)); });
    for (const [action, key] of [['dimensions', 'dimensions'], ['furniture', 'furniture'], ['all-floors', 'all'], ['cutaway', 'cutaway']])
        $(`[data-action="${action}"]`).setAttribute('aria-pressed', String(state[key]));
    $('[data-action="measure"]').setAttribute('aria-pressed', String(state.measurement.active));
    $('#measure-status').textContent = state.measurement.active ? (state.measurement.b ? `القياس: ${fmt(Math.hypot(state.measurement.b.x-state.measurement.a.x,state.measurement.b.y-state.measurement.a.y))} م · انقر لبدء قياس جديد` : state.measurement.a ? 'اختر النقطة الثانية' : 'اختر النقطة الأولى') : 'الوحدة: متر';
    $('#plan-host').classList.toggle('measuring', state.measurement.active);
    $('#plan-host').innerHTML = planSVG(m, state.levelId, { selectedId: state.selectedId, issues, dimensions: state.dimensions, furniture: state.furniture, preview: state.preview, measurement: state.measurement });
    if (!renderer && !$('#scene-error').textContent) {
        try {
            renderer = new StudioRenderer($('#scene'), selectRoom, e => { $('#scene-error').textContent = e; $('#scene-error').hidden = false; });
        }
        catch (e) {
            $('#scene-error').textContent = e.message;
            $('#scene-error').hidden = false;
        }
    }
    renderer?.setModel(m, { levelId: state.levelId, selectedId: state.selectedId, all: state.all, furniture: state.furniture, cutaway: state.cutaway, issues });
    $('#metrics-bar').innerHTML = `<div class="metric"><p>المسطحات الإجمالية</p><strong>${fmt(t.floorArea)}</strong><small>م²</small></div><div class="metric"><p>الخارجية المفاهيمية</p><strong>${fmt(t.outdoorArea)}</strong><small>م²</small></div><div class="metric"><p>كفاءة الحركة</p><strong>${fmt(dm.movement)}</strong><small>/100</small><span class="tiny-up">مؤشر مفاهيمي</span></div><div class="metric score-metric"><p>جودة المفهوم</p><strong>${fmt(dm.overall)}</strong><small>/100</small><span class="tiny-up">ليست اعتمادًا هندسيًا</span></div>`;
    const errors = issues.filter(i => i.status === 'error'), warnings = issues.filter(i => i.status === 'warning'), unchecked = issues.filter(i => i.status === 'unchecked'), checked = issues.filter(i => i.status === 'checked');
    const issueHeadline = errors.length ? (state.preview ? `${errors.length} تعارض في المعاينة — النسخة المحفوظة سليمة` : `${errors.length} مشكلة في النموذج`) : 'فُحص التداخل والوصول وحدود الأرض';
    $('#issues-strip').innerHTML = `${icon(errors.length ? 'alert' : 'shield')}<span class="${errors.length ? '' : 'issue-good'}">${issueHeadline}</span><span class="issue-count">${warnings.length ? `${warnings.length} تنبيه · ` : ''}${checked.length} فحص موثق · ${unchecked.length} لم تُفحص ${icon('chevron')}</span>`;
    renderInspector(r);
    renderPreview();
    $('[data-action="undo"]').disabled = state.readOnly || !!state.preview || state.history.cursor === 0;
    $('[data-action="redo"]').disabled = state.readOnly || !!state.preview || state.undoStack.length === 0;
    $('#command-input').disabled = state.readOnly;
    $('#command-form button[type="submit"]').disabled = state.readOnly;
    $('#assistant-mode').textContent = state.ai ? 'ذكاء سحابي · معاينة فقط' : 'مساعد الأوامر المحلي';
    $('#ai-mode-toggle').textContent = state.ai ? 'سحابي · يرسل بيانات محدودة' : 'محلي · بلا إرسال بيانات';
    if (state.readOnly)
        saveStatus('نسخة مشتركة ثابتة · للقراءة فقط');
    icons();
}
function renderInspector(r) {
    if (!r) {
        $('#inspector-content').innerHTML = '<div class="empty-selection">اختر مساحة من المخطط أو المجسم لعرض خصائصها وعلاقاتها وتعديلها.</div>';
        return;
    }
    const disabled = state.readOnly ? 'disabled' : '', locked = r.locked ? 'disabled' : '', geometryLocked = (r.locked || r.footprint) ? 'disabled' : '', m = shown();
    const dist = distanceToEntry(m, r), garden = touchesGardenEdge(m, r), commentsCount = model().comments.filter(c => c.roomId === r.id && !c.resolved).length;
    $('#inspector-content').innerHTML = `<div class="inspector-selected"><span class="selected-symbol">${icon(['stairs','elevator'].includes(r.kind) ? 'layers' : 'cube')}</span><div><h3>${E(r.name)}</h3><p>${E(KINDS[r.kind])} · ${fmt(area(r))} متر مربع</p></div><button class="icon-button lock-button" data-action="lock" aria-label="${r.locked ? 'إلغاء تثبيت' : 'تثبيت'} العنصر" title="${r.locked ? 'مثبّت: لا تعديل هندسي قبل إلغاء التثبيت' : 'تثبيت هندسة العنصر'}" ${disabled}>${icon(r.locked ? 'lock' : 'unlock')}</button></div>
    <div class="relationship-card"><strong>العلاقات المكانية</strong><div class="relationship-facts"><span>${icon('home')} ${fmt(dist)} م تقريبًا من المدخل</span><span>${icon('image')} ${garden ? 'على جهة الحديقة/الخارج' : 'ليست على الجهة الخارجية'}</span></div>${['stairs','elevator','hall'].includes(r.kind) ? '' : `<div class="quick-relations"><button class="btn light small" data-action="near-entry" ${disabled || locked}>قرب المدخل</button><button class="btn light small" data-action="near-garden" ${disabled || locked}>قرب الحديقة</button></div>`}</div>
    <form id="properties-form"><div class="properties-grid"><label class="field full"><span>اسم المساحة</span><input name="name" maxlength="120" required value="${E(r.name)}" ${disabled}></label>${[['w', 'العرض', r.w], ['d', 'العمق', r.d], ['x', 'الموقع شرقًا', r.x], ['y', 'الموقع شمالًا', r.y]].map(([key, label, value]) => `<label class="field"><span>${label}</span><span class="input-unit"><input aria-label="${label}" name="${key}" type="number" step="0.001" min="${key === 'x' || key === 'y' ? 0 : .5}" max="240" value="${value}" required ${disabled || geometryLocked}><small>م</small></span></label>`).join('')}</div><p class="property-note">${r.locked ? 'هندسة هذا العنصر مثبّتة. ألغِ القفل لتعديلها.' : r.footprint ? 'هذه مساحة غير مستطيلة. حرّكها بالسحب أو عدّلها بأوامر الحدود؛ العرض/العمق المباشران صندوق إحاطة للعرض فقط.' : 'أي تعديل هندسي يمر بمعاينة أثر. التداخل أو تجاوز الأرض يمنع الاعتماد.'}</p><div class="property-actions"><button class="btn primary" type="submit" ${disabled}>${icon('check')}معاينة التعديل</button><button class="btn light" type="button" data-action="door" ${disabled || locked}>${icon('door')}الباب</button><button class="btn light" type="button" data-action="window" ${disabled || locked}>${icon('image')}نافذة</button>${r.footprint?'':`<button class="btn light" type="button" data-action="notch" ${disabled || locked}>${icon('sliders')}تجويف L</button>`}</div></form><div class="detail-row"><span>علاقة المساحة بما حولها</span><button class="text-button" data-action="swap" ${disabled || locked}>مبادلة مساحة ${icon('chevron')}</button></div><div class="detail-row"><span>${icon('message')} ملاحظات المراجعة</span><button class="text-button" data-action="comments">${commentsCount} تعليقات ${icon('chevron')}</button></div>`;
}
function renderPreview() {
    const el = $('#preview-banner'), p = state.preview;
    if (!p) { el.hidden = true; return; }
    el.hidden = false;
    el.className = 'preview-banner' + (p.blockers.length ? ' blocked' : '');
    const impact = p.impact || impactSummary(model(), p.candidate), names = [...new Set(p.changes.map(c => c.name))].join('، '), beforeIssues = validate(model()), newWarnings = p.issues.filter(i => i.status === 'warning' && !beforeIssues.some(j => j.id === i.id));
    p.impact = impact; p.newWarnings = newWarnings;
    const delta = n => `${n > 0 ? '+' : ''}${fmt(n)}`;
    const canResolve = p.blockers.length && p.blockers.some(i => (i.id.startsWith('overlap-') || i.id.startsWith('bounds-')) && i.targets?.some(id => p.changes.some(c => c.id === id)));
    el.innerHTML = `<div class="preview-heading"><div><h3>${p.blockers.length ? 'المعاينة كشفت تعارضًا — لم يتغير المشروع المحفوظ' : p.autoResolved ? 'حل مقترح للتعارض — راجعه قبل الاعتماد' : 'معاينة الأثر — لم يُحفظ بعد'}</h3><p>${p.changes.length} تغييرات · ${impact.affectedIds.length} عناصر متأثرة مباشرة</p></div><div class="preview-actions"><button class="btn light" data-action="cancel-preview">إلغاء</button>${canResolve ? `<button class="btn light" data-action="resolve-preview">${icon('sparkles')} اقتراح حل آمن</button>` : ''}<button class="btn primary" data-action="commit-preview" ${p.blockers.length ? 'disabled' : ''}>اعتماد التعديل</button></div></div><div class="impact-grid"><span><small>المسطحات</small><strong>${delta(impact.floorAreaDelta)} م²</strong></span><span><small>البصمة</small><strong>${delta(impact.footprintDelta)} م²</strong></span><span><small>الحركة</small><strong>${delta(impact.circulationDelta)} م²</strong></span><span><small>مؤشر المفهوم</small><strong>${delta(impact.scoreDelta)} نقطة</strong></span></div><div class="preview-details"><span>المتأثر: ${E(names || 'خصائص المشروع')}. الإطار المتقطع يوضح الوضع السابق.</span>${p.autoResolved ? `<p class="resolved-impact"><strong>اقتراح مسار:</strong> لم نحرّك أي عنصر مثبّت. راجع الحل ثم اعتمده فقط إذا يناسب قصدك.</p>${(p.resolutionNotes||[]).map(n=>`<p class="resolved-impact">✓ ${E(n)}</p>`).join('')}` : ''}${impact.resolvedIssues.filter(i => ['error','warning'].includes(i.status)).map(i => `<p class="resolved-impact">✓ حُلّ: ${E(i.message)}</p>`).join('')}${p.blockers.map(i => `<p>• ${E(i.message)}</p>`).join('')}${newWarnings.length ? `<label><input type="checkbox" id="ack-warnings"> راجعت التنبيهات الجديدة: ${newWarnings.map(i => E(i.message)).join('؛ ')}</label>` : ''}</div>`;
}
function newProject() {
    mutable();
    showModal('صف المشروع كما تتخيله', `<p class="modal-lead">اكتب هدفك بلغة طبيعية. سنستخرج البرنامج والأبعاد والقرارات القابلة للقياس، ثم نعرضها لك قبل إنشاء أي هندسة.</p><form id="new-form"><textarea class="new-prompt" id="new-prompt" name="prompt" maxlength="12000" required placeholder="مثال: أرض 20×25، فيلا 3 أدوار، 5 غرف نوم، مصعد ومسبح، المجلس قرب المدخل والمعيشة على الحديقة. الشارع جنوب.">${E(state.pendingBrief?.prompt||'')}</textarea><div class="template-grid product-templates"><button class="template-card" type="button" data-action="template" data-template="villa">${icon('home')}<span>فيلا عائلية</span><small>3 أدوار · 5 نوم · مصعد</small></button><button class="template-card" type="button" data-action="template" data-template="chalet">${icon('cube')}<span>شاليه</span><small>حديقة · مسبح · جلسات</small></button><button class="template-card" type="button" data-action="template" data-template="office">${icon('layers')}<span>مكاتب</span><small>استقبال · مكاتب · اجتماعات</small></button><button class="template-card" type="button" data-action="template" data-template="warehouse">${icon('cube')}<span>مستودع</span><small>تخزين · تحميل · تشغيل</small></button><button class="template-card" type="button" data-action="template" data-template="retail">${icon('home')}<span>مساحة تجارية</span><small>عرض · تخزين · إدارة</small></button></div><button class="upload-button" type="button" data-action="import">${icon('upload')} استيراد MASAR أو IFC4 أو DXF أو مرجع صورة</button><div class="modal-footer"><p class="upload-hint">المحلل المحلي لا يرسل وصفك إلى الشبكة.<br>الذكاء السحابي اختياري للتعديلات بعد إنشاء المشروع.</p><button class="btn primary" type="submit">تحليل الطلب ${icon('arrow')}</button></div></form>`, '01 — برنامج المشروع');
}
function confirmBrief(brief) {
    state.pendingBrief = brief;
    const source = key => `<small class="source-label">${brief.sources?.[key] === 'requested' ? 'من وصفك' : brief.sources?.[key] === 'derived' ? 'مشتق من نوع المشروع' : 'افتراض — أكّده أو عدّله'}</small>`;
    const projectNames = { villa:'فيلا', chalet:'شاليه', office:'مكاتب', warehouse:'مستودع', retail:'تجاري' };
    showModal('راجع ما فهمه مسار', `<p class="modal-lead">المدخلات التالية هي مصدر الحقيقة لإنشاء النموذج الأول. البنود المعلّمة «من وصفك» تبقى كمتطلبات، والافتراضات لا تتحول إلى حقائق بصمت.</p><form id="brief-form"><div class="brief-confirm-grid"><label class="field"><span>نوع المشروع</span><select name="projectType">${Object.entries(projectNames).map(([v,l])=>`<option value="${v}" ${brief.projectType===v?'selected':''}>${l}</option>`).join('')}</select>${source('projectType')}</label><label class="field"><span>اسم المشروع</span><input name="title" value="${E(brief.title)}" maxlength="120" required></label><label class="field"><span>عرض الأرض</span><input type="number" name="width" value="${brief.width}" min="12" max="120" step="0.1" required>${source('width')}</label><label class="field"><span>عمق الأرض</span><input type="number" name="depth" value="${brief.depth}" min="15" max="160" step="0.1" required>${source('depth')}</label><label class="field"><span>الأدوار إجمالًا</span><input type="number" name="floors" value="${brief.floors}" min="1" max="8" step="1" required>${source('floors')}</label><label class="field"><span>غرف النوم (للسكن)</span><input type="number" name="bedrooms" value="${brief.bedrooms || 0}" min="0" max="16" step="1" required>${source('bedrooms')}</label><label class="field"><span>عدد المكاتب (للمكاتب)</span><input type="number" name="offices" value="${brief.offices || 0}" min="0" max="20" step="1" required>${source('offices')}</label><label class="field"><span>مواقف مطلوبة</span><input type="number" name="parking" value="${brief.parking || 0}" min="0" max="30" step="1" required>${source('parking')}</label><label class="field"><span>جهة الشارع</span><select name="street">${['جنوب','شمال','شرق','غرب'].map(x=>`<option ${x===brief.street?'selected':''}>${x}</option>`).join('')}</select>${source('street')}</label><label class="field"><span>أولوية التوزيع</span><select name="priority">${[['balanced','متوازن'],['privacy','خصوصية'],['outdoor','مساحات خارجية'],['compact','كفاءة ودمج']].map(([v,l])=>`<option value="${v}" ${brief.priority===v?'selected':''}>${l}</option>`).join('')}</select></label><label class="field"><span>طابع العرض</span><select name="style">${[['unspecified','غير محدد'],['modern','حديث'],['classic','كلاسيكي'],['industrial','صناعي']].map(([v,l])=>`<option value="${v}" ${brief.style===v?'selected':''}>${l}</option>`).join('')}</select></label><label class="field"><span>مساحة البناء المطلوبة — من (م²)</span><input type="number" name="buildingAreaMin" min="40" max="50000" step="0.1" value="${brief.buildingAreaMin??''}">${source('buildingArea')}</label><label class="field"><span>مساحة البناء المطلوبة — إلى (م²)</span><input type="number" name="buildingAreaMax" min="40" max="50000" step="0.1" value="${brief.buildingAreaMax??''}"><small>حدود مفاهيمية للغرف؛ اترك الحقلين فارغين عند عدم تحديد المساحة.</small></label></div><div class="feature-checks"><label class="check-line"><input type="checkbox" name="elevator" ${brief.elevator?'checked':''}><span>مصعد مفاهيمي متكرر بين الأدوار</span></label><label class="check-line"><input type="checkbox" name="pool" ${brief.pool?'checked':''}><span>مسبح مفاهيمي ضمن الموقع الخارجي</span></label></div>${brief.intents?.length ? `<div class="notice"><strong>علاقات فهمها النظام:</strong><br>${brief.intents.map(x=>`• ${E(x.label)}`).join('<br>')}</div>`:''}<div class="notice warn">الارتدادات المستخدمة في التوليد <strong>استراتيجية توزيع مفاهيمية</strong> وليست اشتراطات رسمية. لا تُجرى هنا حسابات إنشائية أو تحقق تنظيمي.</div>${brief.buildingAreaMax?'<div class="notice warn">تقييد المساحة لا يعني أن جميع تفاصيل البرنامج تتسع تلقائيًا. الحمام الخاص وغرفة الملابس والبانتري والغسيل والبرجولة والشواء والحمام الخارجي تحتاج تطويرًا ومراجعة منفصلة؛ لا نعدّ حفظ النص تنفيذًا لهذه العناصر.</div>':''}<details class="notice"><summary>الطلب الأصلي كاملًا — التفاصيل غير المقاسة محفوظة للمراجعة</summary><div class="original-prompt">${E(brief.prompt)}</div></details>${brief.unresolved.map(s=>`<p class="notice warn">${E(s)}</p>`).join('')}<label class="check-line"><input type="checkbox" required name="confirm"><span>راجعت البرنامج والأبعاد والافتراضات وأريد إنشاء النموذج المفاهيمي بهذه القيم.</span></label><div class="modal-footer"><button class="btn light" type="button" data-action="new">رجوع</button><button class="btn primary" type="submit">إنشاء المخطط الأول ${icon('arrow')}</button></div></form>`, '02 — تثبيت الفهم');
}
function openBrief() {
    const m = model(), dm = designMetrics(m);
    showModal('طلبك، متطلباتك، وما تحقق منها', `<p class="modal-lead">النص الأصلي محفوظ كما كتبته. المتطلب القابل للقياس يعرض حالته من النموذج الحالي؛ البنود الحرة تبقى للمراجعة البشرية.</p><div class="original-prompt">${E(m.brief.prompt || 'لم يُدخل وصف نصي.')}</div><div class="label-row"><strong>بنود المشروع</strong><button class="text-button green" data-action="add-requirement" ${state.readOnly ? 'disabled' : ''}>إضافة بند</button></div>${m.requirements.map(r=>{const rs=requirementStatus(m,r);return `<div class="req-item"><span class="req-icon">${icon(r.locked?'lock':'unlock')}</span><span><strong>${E(r.label)}</strong>${rs.measurable?`<small class="req-detail">${E(rs.detail)}</small>`:''}</span><span class="source-tag ${rs.measurable&&!rs.satisfied?'warn':rs.measurable&&rs.satisfied?'checked':r.source==='assumed'?'assumed':''}">${rs.measurable?(rs.satisfied?'محقق':'يحتاج تحسين'):(r.source==='assumed'?'افتراض':'مراجعة بشرية')}</span></div>`;}).join('')}<div class="score-summary"><strong>مؤشرات المقارنة المفاهيمية</strong>${[['الخصوصية',dm.privacy],['الحركة',dm.movement],['الخارجية',dm.outdoor],['الكفاءة',dm.efficiency],['المتطلبات القابلة للقياس',dm.requirements]].map(([l,v])=>`<div class="score-row"><span>${l}</span><progress max="100" value="${v}"></progress><b>${fmt(v)}</b></div>`).join('')}<small>${E(dm.note)}</small></div><div class="notice warn">سماكة الجدران وارتفاعاتها في العرض قيم توضيحية. الدرج والمصعد والمسبح هنا كتل/مساحات مفاهيمية وليست تصميمًا تخصصيًا. الهيكل وMEP والحريق والإتاحة والاشتراطات التنظيمية تبقى «لم تُفحص» حتى ربط أدوات تحقق متخصصة واعتماد مختص.</div>`);
}
async function projects() {
    await saveQueue;
    let rows = [];
    try {
        rows = await listLocal();
    }
    catch (e) {
        reportError(e);
    }
    const local = `<div class="label-row"><strong>على هذا الجهاز</strong><span class="muted">${rows.length} مشاريع</span></div><div class="projects-list">${rows.length ? rows.map(p => `<div class="project-card">${icon('folder')}<div class="info"><h3>${E(p.title)}</h3><p>${E(new Date(p.updated).toLocaleString('ar-SA'))} · ${p.history.revisions.length} نسخ</p></div><button class="btn light" data-action="open-local" data-id="${E(p.id)}">فتح</button><button class="icon-button" data-action="delete-local" data-id="${E(p.id)}" aria-label="حذف المشروع المحلي">${icon('trash')}</button></div>`).join('') : '<p class="notice">لا توجد مشاريع محفوظة على هذا الجهاز بعد.</p>'}</div>`;
    let cloud = '';
    if (api.user) {
        try {
            const data = await api.request('/api/projects');
            cloud = `<div class="label-row"><strong>حسابك على الخادم</strong><button class="text-button green" data-action="save-cloud">حفظ المشروع الحالي هنا</button></div><div class="projects-list">${data.projects.map(p => `<div class="project-card">${icon('cloud')}<div class="info"><h3>${E(p.title)}</h3><p>نسخة الخادم ${p.version}</p></div><button class="btn light" data-action="open-cloud" data-id="${E(p.id)}">فتح</button></div>`).join('') || '<p class="notice">لم تحفظ مشروعًا على الخادم بعد.</p>'}</div>`;
        }
        catch (e) {
            cloud = `<p class="notice error">${E(e.message)}</p>`;
        }
    }
    showModal('مساحة مشاريعك', `<p class="modal-lead">الحفظ المحلي داخل هذا المتصفح فقط. نزّل نسخة JSON احتياطية؛ مسح بيانات المتصفح يزيل المشاريع المحلية.</p>${local}${cloud}<div class="modal-footer"><button class="btn light" data-action="import">${icon('upload')}استيراد مشروع</button><button class="btn primary" data-action="new">${icon('plus')}مشروع جديد</button></div>`);
}
function openHistory() {
    showModal('كل قرار له نسخة', `<p class="modal-lead">استعادة نسخة قديمة تنشئ نسخة جديدة، ولا تكتب فوق الأصل. تستطيع أيضًا مقارنة نسختين دون تغيير المشروع.</p><div class="history-list">${state.history.revisions.map((r, i) => ({ r, i })).reverse().map(({ r, i }) => `<div class="revision-item ${i === state.history.cursor ? 'current' : ''}"><span class="revision-dot"></span><div><h3>${E(r.label)}</h3><p>${E(new Date(r.at).toLocaleString('ar-SA'))}${i === state.history.cursor ? ' · النسخة الحالية' : ''}</p></div><button class="btn light" data-action="restore" data-index="${i}" ${state.readOnly || i === state.history.cursor ? 'disabled' : ''}>استعادة</button></div>`).join('')}</div><div class="modal-footer"><span class="upload-hint">${state.history.revisions.length} / 100 نسخة محفوظة</span><button class="btn light" data-action="compare-revisions" ${state.history.revisions.length < 2 ? 'disabled' : ''}>مقارنة نسختين</button><button class="btn primary" data-action="name-revision" ${state.readOnly ? 'disabled' : ''}>حفظ نسخة مسماة</button></div>`);
}
function revisionCompareForm() {
    const currentIndex=state.history.cursor, prev=currentIndex>0?currentIndex-1:Math.min(1,state.history.revisions.length-1);
    const options=selectedIndex=>state.history.revisions.map((r,i)=>`<option value="${i}" ${i===selectedIndex?'selected':''}>${E(r.label)} · ${E(new Date(r.at).toLocaleString('ar-SA'))}</option>`).join('');
    showModal('مقارنة نسختين', `<p class="modal-lead">المقارنة للقراءة فقط؛ لا تنشئ نسخة ولا تغيّر الهندسة.</p><form id="compare-form"><div class="brief-confirm-grid"><label class="field"><span>النسخة السابقة</span><select name="before">${options(prev)}</select></label><label class="field"><span>النسخة اللاحقة</span><select name="after">${options(currentIndex)}</select></label></div><div class="modal-footer"><button class="btn primary" type="submit">إظهار الفروق</button></div></form>`);
}
function revisionComparison(beforeIndex, afterIndex) {
    const a=state.history.revisions[beforeIndex], b=state.history.revisions[afterIndex];
    if(!a||!b||beforeIndex===afterIndex) throw Error('اختر نسختين مختلفتين للمقارنة.');
    const changes=diffModels(a.model,b.model), ta=totals(a.model), tb=totals(b.model), ma=designMetrics(a.model), mb=designMetrics(b.model), ga=deriveBuildingGraph(a.model).counts, gb=deriveBuildingGraph(b.model).counts;
    const delta=n=>`${n>0?'+':''}${fmt(n)}`;
    const fieldNames={name:'الاسم',kind:'النوع',x:'الموقع شرقًا',y:'الموقع شمالًا',w:'العرض',d:'العمق',height:'الارتفاع',locked:'التثبيت',footprint:'المضلع',doors:'الأبواب',windows:'النوافذ',authoring:'أنواع الجدران',note:'الملاحظة'};
    showModal('فروق النسختين', `<p class="modal-lead"><strong>${E(a.label)}</strong> ← <strong>${E(b.label)}</strong>. هذه قراءة مقارنة فقط.</p><div class="impact-grid"><div><span>المسطحات</span><strong>${delta(tb.floorArea-ta.floorArea)} م²</strong></div><div><span>المساحات</span><strong>${delta(gb.spaces-ga.spaces)}</strong></div><div><span>الجدران المشتقة</span><strong>${delta(gb.walls-ga.walls)}</strong></div><div><span>الأبواب والنوافذ</span><strong>${delta(gb.openings-ga.openings)}</strong></div><div><span>مؤشر المفهوم</span><strong>${delta(mb.overall-ma.overall)}</strong></div><div><span>الحركة</span><strong>${delta(mb.movement-ma.movement)}</strong></div></div><div class="label-row"><strong>${changes.length} عناصر تغيّرت</strong></div>${changes.length?`<div class="history-list">${changes.map(c=>`<div class="revision-item"><span class="revision-dot"></span><div><h3>${E(c.name)}</h3><p>${c.kind==='added'?'أضيف':c.kind==='removed'?'حُذف':`تغيّر: ${c.fields.map(f=>fieldNames[f]||f).join('، ')}`}</p></div></div>`).join('')}</div>`:'<div class="notice">لا توجد فروق على مستوى المساحات بين النسختين.</div>'}<div class="notice">مؤشرات الجودة هنا للمقارنة المفاهيمية فقط. المقارنة لا تعني تحققًا إنشائيًا أو تنظيميًا.</div><div class="modal-footer"><button class="btn light" data-action="compare-revisions">اختيار نسختين أخريين</button><button class="btn primary" data-action="history">العودة للتاريخ</button></div>`);
}

function openIssues() {
    const items = validate(shown()), errors = items.filter(i=>i.status==='error'), warnings = items.filter(i=>i.status==='warning'), checked=items.filter(i=>i.status==='checked'), unchecked=items.filter(i=>i.status==='unchecked');
    const label={error:'به مشكلة',warning:'تنبيه',checked:'فُحص',unchecked:'لم يُفحص'};
    showModal('مركز الفحص والحدود', `<p class="modal-lead">نفرّق صراحة بين ما فحصه المحرك وما لم يفحصه. «فُحص» يعني تحققًا داخل نموذج MASAR فقط، ولا يعني اعتماد كود أو سلامة إنشائية.</p><div class="issue-summary-grid"><span class="error"><b>${errors.length}</b> مشكلة</span><span class="warning"><b>${warnings.length}</b> تنبيه</span><span class="checked"><b>${checked.length}</b> فُحص</span><span class="unchecked"><b>${unchecked.length}</b> لم يُفحص</span></div>${items.map(i=>`<button class="issue-item ${i.status}" data-action="focus-issue" data-id="${E(i.targets[0]||'')}"><span class="issue-status">${label[i.status]||i.status}</span><p>${E(i.message)}</p>${i.targets.length?`<small>${icon('chevron')}</small>`:''}</button>`).join('')}`);
}
function openModelHealth() {
    const m=shown(), graph=deriveBuildingGraph(m), ready=projectReadiness(m), ruleEval=evaluateRulePack(m), requirements=requirementMatrix(m);
    const attention=ruleEval.results.filter(r=>r.status!=='pass');
    const reqDone=requirements.filter(r=>r.measurable&&r.satisfied).length, reqMeasurable=requirements.filter(r=>r.measurable).length;
    showModal('نموذج المبنى وجودة التسليم', `<p class="modal-lead">هذه طبقة مشتقة من نموذج المشروع نفسه: المساحات → الجدران → الفتحات → البلاطات والسقف. لا تتحول الطبقة المشتقة إلى مصدر حقيقة عكسي، ولا تعني اعتماد BIM تنفيذي أو كود بناء.</p><div class="issue-summary-grid"><span class="checked"><b>${graph.counts.spaces}</b> مساحة</span><span class="checked"><b>${graph.counts.walls}</b> جدارًا مشتقًا</span><span class="checked"><b>${graph.counts.doors}</b> أبواب · ${graph.counts.windows} نوافذ</span><span class="checked"><b>${graph.counts.slabs + graph.counts.roofs}</b> بلاطات/سقف</span></div><div class="score-summary"><strong>جاهزية النموذج المفاهيمي</strong><div class="score-row"><span>أخطاء النموذج</span><progress max="10" value="${Math.min(10,ready.validation.errors)}"></progress><b>${ready.validation.errors}</b></div><div class="score-row"><span>متطلبات قابلة للقياس</span><progress max="${Math.max(1,reqMeasurable)}" value="${reqDone}"></progress><b>${reqDone}/${reqMeasurable}</b></div><div class="score-row"><span>قواعد جودة تحتاج مراجعة</span><progress max="${Math.max(1,ruleEval.summary.pass+ruleEval.summary.review+ruleEval.summary.fail)}" value="${ruleEval.summary.review+ruleEval.summary.fail}"></progress><b>${ruleEval.summary.review+ruleEval.summary.fail}</b></div></div><div class="notice ${ready.deliveryReady?'':'warn'}"><strong>${ready.deliveryReady?'النموذج متسق للتسليم المفاهيمي.':'النموذج يحتاج معالجة قبل التسليم المفاهيمي.'}</strong><br>${E(ready.note)}</div><div class="label-row"><strong>حزمة الجودة: ${E(ruleEval.pack.name)} / ${E(ruleEval.pack.version)}</strong><span class="muted">ليست حزمة امتثال</span></div>${attention.length?attention.slice(0,30).map(r=>`<div class="issue-item ${r.status==='fail'?'error':'warning'}"><span class="issue-status">${r.status==='fail'?'تعذر':'مراجعة'}</span><p>${E(r.message)}</p></div>`).join(''):'<p class="notice">لا توجد عناصر مراجعة في حزمة الجودة المفاهيمية الحالية.</p>'}<div class="notice warn"><strong>غير مفحوص هندسيًا/تنظيميًا:</strong> ${ready.validation.unchecked} بندًا ظاهرًا في مركز الفحص. حالة «جاهز للتسليم المفاهيمي» لا تغيّرها إلى PASS ولا تعني صلاحية البناء.</div><div class="modal-footer"><button class="btn light" data-action="building-elements">جدول العناصر</button><button class="btn light" data-action="requirements-center">مصفوفة المتطلبات</button><button class="btn light" data-action="export">${icon('download')} ملفات التسليم</button><button class="btn primary" data-action="issues">${icon('shield')} مركز الفحص</button></div>`, 'BUILDING MODEL / QA');
}

function buildingElements() {
    const g=deriveBuildingGraph(shown()), labels={window:'نافذة',space:'مساحة',wall:'جدار',door:'باب',slab:'بلاطة',roof:'سقف',siteFeature:'عنصر موقع'};
    const rows=[...g.elements.spaces.map(x=>({...x,_category:'space'})),...g.elements.walls.map(x=>({...x,_category:'wall'})),...g.elements.openings.map(x=>({...x,_category:x.type==='window'?'window':'door'})),...g.elements.slabs.map(x=>({...x,_category:'slab'})),...g.elements.roofs.map(x=>({...x,_category:'roof'})),...(g.elements.siteFeatures||[]).map(x=>({...x,_category:'siteFeature'}))];
    showModal('جدول عناصر نموذج المبنى', `<p class="modal-lead">هوية العناصر المشتقة تُحسب من النموذج الحالي. الجدران والبلاطات والسقف مشتقات للتنسيق وليست عناصر BIM تنفيذية مستقلة.</p><div class="history-list">${rows.slice(0,250).map(x=>`<div class="revision-item"><span class="revision-dot"></span><div><h3>${E(x.name||labels[x._category]||'عنصر')}</h3><p>${E(labels[x._category]||'عنصر')} · ${E(x.id)}${x.length?` · ${fmt(x.length)} م`:''}${x.area?` · ${fmt(x.area)} م²`:''}${x.levelId?` · ${E(x.levelId)}`:''}</p></div></div>`).join('')}</div>${rows.length>250?`<div class="notice">يعرض المركز أول 250 عنصرًا من ${rows.length}. نزّل CSV للحصول على القائمة الكاملة.</div>`:''}<div class="modal-footer"><button class="btn light" data-action="model-health">العودة</button><button class="btn primary" data-action="download" data-kind="elements">تنزيل CSV</button></div>`, 'DERIVED ELEMENT SCHEDULE');
}
function requirementsCenter() {
    const rows=requirementMatrix(shown());
    showModal('مصفوفة متطلبات المشروع', `<p class="modal-lead">يفصل المركز بين المتطلب القابل للقياس والبند الذي يحتاج قرارًا أو مراجعة بشرية. لا تُرقّى البنود غير المقاسة إلى «محقق».</p><div class="history-list">${rows.map(r=>`<div class="revision-item"><span class="revision-dot"></span><div><h3>${E(r.label)}</h3><p>${r.measurable?(r.satisfied?'محقق داخل نموذج مسار':'يحتاج تحسين'):'مراجعة بشرية'} · المصدر: ${E(r.source)} · ${r.locked?'مثبّت':'غير مثبّت'}</p></div></div>`).join('')}</div><div class="modal-footer"><button class="btn light" data-action="model-health">العودة</button><button class="btn primary" data-action="download" data-kind="requirements">تنزيل CSV</button></div>`, 'REQUIREMENTS TRACEABILITY');
}
function openAlternatives() {
    mutable();
    state.alternatives = createAlternatives(model());
    const baseScore=state.alternatives[0].metrics.overall;
    showModal('بدائل محسوبة مع بقاء قراراتك المثبتة', `<p class="modal-lead">يولّد مسار أربع قراءات حتمية للمساحات الحالية، ويقارنها بمؤشرات معلنة. المؤشرات أدوات قرار داخلية وليست تقييمًا معماريًا مهنيًا أو فحص كود.</p><div class="alternate-grid">${state.alternatives.map((a,i)=>{const t=totals(a.model),d=a.metrics.overall-baseScore;return `<div class="alternate-card"><div class="alternate-plan">${planSVG(a.model,state.levelId,{dimensions:false,furniture:false,interactive:false,issues:validate(a.model)})}</div><div class="alternate-info"><h3>${E(a.label)}</h3><p>${E(a.description)}</p><div class="alt-metrics"><span>المفهوم <b>${fmt(a.metrics.overall)}</b></span><span>الخصوصية <b>${fmt(a.metrics.privacy)}</b></span><span>الحركة <b>${fmt(a.metrics.movement)}</b></span><span>الخارجية <b>${fmt(a.metrics.outdoor)}</b></span></div><p>${fmt(t.floorArea)} م² مسطحات · ${fmt(t.outdoorArea)} م² خارجية<br>فرق المؤشر عن الحالي: ${d>0?'+':''}${fmt(d)}</p><button class="btn ${i?'primary':'light'} full" data-action="use-alternative" data-index="${i}" ${i===0?'disabled':''}>معاينة هذا البديل</button></div></div>`;}).join('')}</div><div class="notice">العناصر المثبتة لا تتحرك. أي بديل ينتج تعارضًا هندسيًا سيُمنع عند المعاينة، وكل اعتماد يُنشئ نسخة جديدة قابلة للتراجع.</div>`, '03 — مقارنة البدائل');
}
function download(filename, content, type) { const blob = content instanceof Blob ? content : new Blob([content], { type }); const href = URL.createObjectURL(blob), a = document.createElement('a'); a.href = href; a.download = filename; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(href), 30000); toast('جُهّز الملف للتنزيل.'); }
function exportMenu() {
    showModal('تسليم المشروع', `<p class="modal-lead">كل ملف يحمل معنى واضحًا. ملفات DXF/OBJ/SVG مخرجات هندسية مفاهيمية وليست BIM تنفيذيًا.</p><div class="export-grid">${[['json','file','مشروع MASAR JSON','النموذج والمتطلبات والتعليقات وسجل النسخ للاستعادة.'],['svg','image','مخطط SVG','مخطط متجهي للدور الحالي.'],['dxf','ruler','DXF مفاهيمي','حدود الغرف بالمتر كمرجع CAD.'],['ifc','cube','IFC4 مع فتحات مستضافة','مساحات وجدران بطبقات وبلاطات وأبواب ونوافذ وفتحات للتنسيق. يدعم المستورد مجموعة فرعية فقط.'],['obj','cube','OBJ ثلاثي الأبعاد','كتل العرض المفاهيمي ثلاثية الأبعاد.'],['csv','file','جدول المساحات CSV','جدول الغرف والأبعاد والمساحات لكل الأدوار.'],['elements','file','جدول عناصر المبنى CSV','مساحات وجدران وأبواب وبلاطات وسقف مع الهوية والمنشأ.'],['requirements','file','مصفوفة المتطلبات CSV','المصدر والتثبيت وقابلية القياس والحالة لكل متطلب.'],['rules','shield','نتيجة حزمة الجودة JSON','نتائج حزمة MASAR المفاهيمية وإثبات أنها ليست حزمة امتثال.'],['report','file','تقرير تسليم HTML','المتطلبات، المؤشرات، الفحوص والمخططات والجداول.'],['png','image','لقطة PNG','لقطة العرض الحالي بعلامة غير صالح للبناء.']].map(([kind,ic,title,desc])=>`<button class="export-option" data-action="download" data-kind="${kind}">${icon(ic)}<strong>${title}</strong><p>${desc}</p></button>`).join('')}</div>`);
}
function roomScheduleCSV() {
    const rows=[['Level','Room','Kind','Width_m','Depth_m','Area_m2','X_m','Y_m','Locked']];
    for(const l of model().levels) for(const r of l.rooms) rows.push([l.name,r.name,KINDS[r.kind],r.w,r.d,area(r),r.x,r.y,r.locked?'yes':'no']);
    const esc=csvCell;
    return '\uFEFF'+rows.map(row=>row.map(esc).join(',')).join('\r\n');
}
function reportHTML() {
    const m=model(),t=totals(m),issues=validate(m),dm=designMetrics(m), graph=deriveBuildingGraph(m), rules=evaluateRulePack(m), ready=projectReadiness(m), reqMatrix=requirementMatrix(m), status={error:'به مشكلة',warning:'تنبيه',checked:'فُحص داخل النموذج',unchecked:'لم يُفحص'};
    return `<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>تسليم ${E(m.title)}</title><style>body{font:15px Tahoma,Arial;line-height:1.9;max-width:1080px;margin:40px auto;padding:25px;color:#244332}h1{font-size:30px}h2{font-size:20px;border-bottom:1px solid #ddd;padding-bottom:10px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;padding:9px;text-align:right}.notice{padding:18px;background:#f6f1e6}.score{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}.score span{border:1px solid #ddd;padding:10px}svg{max-height:700px;width:100%}pre{white-space:pre-wrap}small{color:#667}@media print{body{margin:0;padding:0}section{break-inside:avoid}}</style><h1>مسار | ${E(m.title)}</h1><small>نسخة ${E(state.history.revisions[state.history.cursor].id)} · ${E(new Date().toISOString())} · جميع الأبعاد بالمتر</small><p class="notice"><strong>تصميم مفاهيمي — NOT FOR CONSTRUCTION.</strong> لا يثبت هذا التقرير مطابقة كود البناء أو سلامة المنشأ أو كفاية أنظمة الحريق/MEP/الإتاحة. يلزم اعتماد المختصين قبل التنفيذ.</p><h2>الطلب الأصلي</h2><pre>${E(m.brief.prompt)}</pre><h2>إعدادات المفهوم</h2><p>النوع: ${E(m.design?.projectType||'villa')} · المرحلة: ${E(m.design?.stage||'concept')} · الأولوية: ${E(m.design?.priority||'balanced')} · الطابع: ${E(m.design?.style||'unspecified')}</p><h2>ملخص المساحات</h2><p>الأرض ${fmt(t.landArea)} م² · المسطحات ${fmt(t.floorArea)} م² · بصمة الأرضي ${fmt(t.footprint)} م² · الخارجية ${fmt(t.outdoorArea)} م² · الحركة ${fmt(t.circulation)} م² (${fmt(t.circulationPct)}%)</p><div class="score"><span>المفهوم<br><b>${fmt(dm.overall)}/100</b></span><span>الخصوصية<br><b>${fmt(dm.privacy)}</b></span><span>الحركة<br><b>${fmt(dm.movement)}</b></span><span>الخارجية<br><b>${fmt(dm.outdoor)}</b></span><span>الكفاءة<br><b>${fmt(dm.efficiency)}</b></span></div><small>${E(dm.note)}</small><h2>المتطلبات</h2><table><tr><th>البند</th><th>المصدر</th><th>الحالة</th><th>التفصيل</th></tr>${m.requirements.map(r=>{const rs=requirementStatus(m,r);return `<tr><td>${E(r.label)}</td><td>${E(r.source||'requested')}</td><td>${rs.measurable?(rs.satisfied?'محقق':'يحتاج تحسين'):'مراجعة بشرية'}</td><td>${E(rs.detail)}</td></tr>`;}).join('')}</table><h2>نموذج المبنى المشتق</h2><p>${graph.counts.spaces} مساحة · ${graph.counts.walls} جدارًا مشتقًا · ${graph.counts.doors} أبواب · ${graph.counts.windows} نوافذ · ${graph.counts.slabs} بلاطات · ${graph.counts.roofs} سقف. هذه مشتقات تنسيق من نموذج المساحات وليست عناصر BIM تنفيذية مستقلة.</p><h2>جاهزية التسليم المفاهيمي</h2><p>${ready.deliveryReady?'متسق داخل نطاق مسار المفاهيمي':'يحتاج معالجة داخل نموذج مسار'} · المتطلبات القابلة للقياس ${ready.requirements.satisfied}/${ready.requirements.measurable} · نتائج الجودة: ${rules.summary.pass} اجتازت، ${rules.summary.review} مراجعة، ${rules.summary.fail} تعذّر، ${rules.summary.unchecked} غير مفحوص.</p><p><strong>${E(rules.pack.name)} ${E(rules.pack.version)}</strong> — ${E(rules.pack.disclaimer)}</p>${m.levels.map(l=>`<section><h2>${E(l.name)}</h2>${planSVG(m,l.id,{interactive:false,issues})}<table><thead><tr><th>المساحة</th><th>النوع</th><th>العرض</th><th>العمق</th><th>المساحة</th><th>الحالة</th></tr></thead><tbody>${l.rooms.map(r=>`<tr><td>${E(r.name)}</td><td>${E(KINDS[r.kind])}</td><td>${fmt(r.w)}</td><td>${fmt(r.d)}</td><td>${fmt(area(r))}</td><td>${r.locked?'مثبت':'قابل للتعديل'}</td></tr>`).join('')}</tbody></table></section>`).join('')}<h2>الفحص وحدوده</h2>${issues.map(i=>`<p><strong>${status[i.status]||E(i.status)}:</strong> ${E(i.message)}</p>`).join('')}<h2>تعليقات المراجعة</h2>${m.comments.map(c=>`<p>${E(c.text)} — ${E(c.author)} (${c.resolved?'مغلق':'مفتوح'})</p>`).join('')||'<p>لا توجد تعليقات.</p>'}<h2>قبل التنفيذ</h2><p>تثبيت متطلبات المالك والموقع؛ التحقق من الأنظمة والارتدادات الفعلية؛ تطوير معماري تفصيلي؛ تصميم واعتماد الإنشاء وMEP والحريق والإتاحة؛ تنسيق التخصصات؛ إصدار رسومات مختومة من الجهات المختصة.</p></html>`;
}
async function account(mode = 'login') {
    state.authMode = mode;
    if (!api.available) {
        showModal('الحسابات تحتاج تشغيل الخادم', `<p class="modal-lead">أنت تستخدم النسخة المحلية من الاستوديو. الرسم والتعديل والحفظ على الجهاز والتصدير متاحة.</p><div class="notice">لتفعيل الحسابات والحفظ على الخادم وروابط المراجعة، شغّل النسخة الكاملة بالأمر <code dir="ltr">npm start</code> وافتح العنوان المحلي الذي يظهر. لا تُرسل مفاتيح API عبر الواجهة.</div>`);
        return;
    }
    if (api.user) {
        showModal('حسابك ومساحة التخزين', `<p class="modal-lead">مرحبًا ${E(api.user.name)}. ${E(api.user.email)}</p><div class="notice">الحفظ المحلي لا يعني حفظًا على حسابك. الحفظ السحابي هنا هو على خادم MASAR الذي تشغّله أو تنشره.</div><div class="account-actions"><button class="btn primary" data-action="save-cloud">حفظ المشروع على حسابي</button><button class="btn light" data-action="change-password">تغيير كلمة المرور</button><button class="btn light" data-action="logout">تسجيل الخروج</button><button class="btn danger" data-action="delete-account">حذف الحساب وبياناته</button></div>`);
        return;
    }
    showModal(mode === 'register' ? 'إنشاء حساب' : 'تسجيل الدخول', `<p class="modal-lead">الحساب اختياري للعمل المحلي، ومطلوب للحفظ على الخادم والمشاركة. تفعيل البريد واستعادة كلمة المرور عبر البريد غير متاحين في هذه النسخة.</p><form id="auth-form" class="auth-form">${mode === 'register' ? '<label class="field"><span>الاسم</span><input name="name" maxlength="120" required autocomplete="name"></label>' : ''}<label class="field"><span>البريد الإلكتروني</span><input name="email" type="email" maxlength="200" required autocomplete="email" dir="ltr"></label><label class="field"><span>كلمة المرور ${mode === 'register' ? '(12 حرفًا على الأقل)' : ''}</span><input name="password" type="password" minlength="${mode === 'register' ? 12 : 1}" maxlength="200" required autocomplete="${mode === 'register' ? 'new-password' : 'current-password'}" dir="ltr"></label><button class="btn primary" type="submit">${mode === 'register' ? 'إنشاء الحساب' : 'دخول'}</button><div id="auth-error" role="alert"></div></form>${api.registration ? `<div class="auth-toggle"><button class="text-button green" data-action="auth-mode" data-mode="${mode === 'register' ? 'login' : 'register'}">${mode === 'register' ? 'لدي حساب بالفعل' : 'إنشاء حساب جديد'}</button></div>` : ''}`);
}
async function saveCloud() {
 if(state.readOnly)throw Error('رابط المراجعة للقراءة فقط.');
 if(!api.user){await account();return;}
 if(state.preview)throw Error('اعتمد المعاينة أو ألغها قبل الحفظ على الخادم.');
 const snapshot=clone(state.history),key=api.user.id+':'+snapshot.projectId,version=state.versions.get(key)||0;
 let result;
 try{result=await api.request('/api/projects/'+encodeURIComponent(snapshot.projectId),{method:'PUT',body:{history:snapshot,version}});}
 catch(error){
  if(error.status===409)showModal('توجد نسخة أحدث على الخادم',`<p class="notice warn">لم تُستبدل النسخة الأحدث، ولم يتغير عملك المفتوح. نزّل نسخة JSON من عملك أولًا. يمكنك فتح نسخة الخادم، أو حفظ العمل الحالي كمشروع مستقل دون حذف المشروع السابق.</p><div class="modal-footer"><button class="btn light" data-action="download" data-kind="json">تنزيل عملي الحالي</button><button class="btn light" data-action="open-cloud" data-id="${E(snapshot.projectId)}">فتح نسخة الخادم</button><button class="btn primary" data-action="fork-project">إنشاء نسخة مستقلة</button></div>`);
  throw error;
 }
 state.versions.set(key,result.version);await persist();if(JSON.stringify(state.history)===JSON.stringify(snapshot)){saveStatus(`محفوظ على الخادم · نسخة ${result.version}`);toast('حُفظت نسخة المشروع على حسابك.');}else toast('حُفظت النسخة المرسلة؛ التعديلات اللاحقة ما زالت محلية وتحتاج حفظًا آخر.');return result;
}
async function share() { if (state.readOnly) {
    toast('هذا بالفعل رابط مراجعة للقراءة فقط.');
    return;
} if (!api.user) {
    await account();
    return;
} const list = await api.request('/api/shares'); showModal('مشاركة نسخة للمراجعة', `<p class="modal-lead">الرابط يعرض لقطة ثابتة للقراءة فقط. أي شخص يملك الرابط يستطيع الاطلاع على المحتوى الذي تختاره، ويمكنك إلغاء الرابط في أي وقت.</p><form id="share-form"><label class="field"><span>مدة صلاحية الرابط</span><select name="days"><option value="1">يوم واحد</option><option value="7" selected>7 أيام</option><option value="30">30 يومًا</option></select></label><label class="check-line"><input type="checkbox" name="includeComments"><span>تضمين تعليقات المراجعة وأسماء أصحابها. تُستبعد افتراضيًا.</span></label><label class="check-line"><input type="checkbox" name="includePrompt"><span>تضمين وصف المشروع الأصلي. يُستبعد افتراضيًا.</span></label><label class="check-line"><input type="checkbox" name="consent" required><span>أوافق على مشاركة نموذج هذا المشروع عبر رابط قابل للتداول.</span></label><button class="btn primary" type="submit">حفظ المشروع وإنشاء الرابط</button></form><div id="share-result"></div><div class="label-row"><strong>روابط هذا المشروع</strong><button class="text-button green" data-action="review-center">تعليقات المراجعين</button></div>${list.shares.filter(s => s.project_id === model().id).map(s => `<div class="project-card"><div class="info"><h3>${s.expires > Date.now() ? 'رابط نشط' : 'رابط منتهي'}</h3><p>الانتهاء: ${E(new Date(s.expires).toLocaleDateString('ar-SA'))}</p></div><button class="btn danger" data-action="revoke-share" data-id="${E(s.id)}">إلغاء الرابط</button></div>`).join('') || '<p class="notice">لم تنشئ رابط مراجعة لهذا المشروع.</p>'}`); }
async function comments() {
    const r = selected(); if (!r) throw Error('اختر مساحة لإضافة تعليق مرتبط بها.');
    if (state.readOnly && state.shareToken && api.available) {
        const data=await api.request('/api/shares/'+encodeURIComponent(state.shareToken)+'/comments'), list=data.comments.filter(c=>c.targetId===r.id);
        showModal('مراجعة مشتركة: '+r.name, `<p class="modal-lead">تعليقات المراجعين منفصلة عن لقطة المشروع ولا تغيّر هندسته. يستطيع مالك المشروع قراءتها وإغلاقها من مركز المراجعات.</p><div class="comments-list">${list.map(c=>`<div class="comment-item"><p>${E(c.text)}</p><div class="comment-meta"><span>${E(c.author)} · ${E(new Date(c.created).toLocaleDateString('ar-SA'))}</span></div><small>${c.resolved?'مغلق بواسطة المالك':'مفتوح'}</small></div>`).join('')||'<p class="notice">لا توجد تعليقات مراجعين على هذه المساحة بعد.</p>'}</div><form id="review-comment-form"><input type="hidden" name="targetId" value="${E(r.id)}"><label class="field"><span>اسم المراجع</span><input name="author" maxlength="80" required autocomplete="name"></label><label class="field full"><span>الملاحظة</span><textarea name="text" rows="3" maxlength="1200" required placeholder="اكتب ملاحظتك على هذه المساحة"></textarea></label><div class="notice">لن يطبق التعليق أي تعديل. هو طلب مراجعة فقط.</div><div class="modal-footer"><button class="btn primary" type="submit">إرسال الملاحظة</button></div></form>`,'REVIEW LINK');
        return;
    }
    const list = model().comments.filter(c => c.roomId === r.id);
    showModal('مراجعة: ' + r.name, `<p class="modal-lead">التعليقات مرتبطة بهوية المساحة، وتبقى معها عند تغيير موضعها.</p><div class="comments-list">${list.map(c => `<div class="comment-item"><p>${E(c.text)}</p><div class="comment-meta"><span>${E(c.author)} · ${E(new Date(c.at).toLocaleDateString('ar-SA'))}</span><button class="text-button" data-action="resolve-comment" data-id="${E(c.id)}">${c.resolved ? 'إعادة فتح' : 'إغلاق التعليق'}</button></div><small>${c.resolved ? 'مغلق' : 'مفتوح'}</small></div>`).join('') || '<p class="notice">لا توجد تعليقات على هذه المساحة.</p>'}</div><form id="comment-form"><label class="field full" style="margin-top:20px"><span>ملاحظتك</span><textarea name="text" rows="3" maxlength="2000" required></textarea></label><div class="modal-footer"><span class="upload-hint">الكاتب: ${E(api.user?.name || 'مالك المشروع')}</span><button class="btn primary" type="submit">إضافة تعليق</button></div></form>`);
}
async function reviewCenter() {
    if (!api.user) { await account(); return; }
    const data=await api.request('/api/projects/'+encodeURIComponent(model().id)+'/review-comments'), roomNames=new Map(model().levels.flatMap(l=>l.rooms).map(r=>[r.id,r.name]));
    showModal('تعليقات روابط المراجعة', `<p class="modal-lead">هذه ملاحظات أرسلها أشخاص عبر روابط المراجعة. لا تُدمج تلقائيًا في النموذج ولا تنشئ تعديلات.</p>${data.comments.length?`<div class="comments-list">${data.comments.map(c=>`<div class="comment-item"><p>${E(c.text)}</p><div class="comment-meta"><span>${E(c.author)} · ${E(new Date(c.created).toLocaleString('ar-SA'))}${c.targetId?` · ${E(roomNames.get(c.targetId)||'عنصر من نسخة مشاركة')}`:''}</span><button class="text-button" data-action="resolve-review-comment" data-id="${E(c.id)}" data-resolved="${c.resolved?'false':'true'}">${c.resolved?'إعادة فتح':'إغلاق'}</button></div><small>${c.resolved?'مغلق':'مفتوح'} · ${c.expires>Date.now()?'الرابط ما زال صالحًا':'الرابط منتهي'}</small></div>`).join('')}</div>`:'<p class="notice">لا توجد ملاحظات واردة من روابط المراجعة.</p>'}`, 'REVIEW INBOX');
}
function switchMobile(panel) { $('.studio-layout').classList.toggle('show-project', panel === 'project'); $('.studio-layout').classList.toggle('show-inspector', panel === 'inspector'); $$('[data-action="mobile"]').forEach(b => b.classList.toggle('active', b.dataset.panel === panel)); requestAnimationFrame(() => renderer?.draw()); }
function setProject(history, { demo = false, readOnly = false, shareToken = null } = {}) { assertHistory(history); state.history = history; state.demo = demo; state.readOnly = readOnly; state.shareToken = shareToken; state.preview = null; state.undoStack = []; state.measurement = { active:false, a:null, b:null }; state.levelId = model().levels[0].id; state.selectedId = model().levels[0].rooms.find(r => r.kind === 'majlis')?.id || model().levels[0].rooms[0]?.id; state.dirty = false; state.saveError = null; if (!readOnly && location.search)
    historyAPI.replaceState({}, '', location.pathname); render(); }
const historyAPI = window.history;
async function handleAction(b) {
    const action = b.dataset.action;
    switch (action) {
        case 'dismiss-toast':
            b.closest('.toast').remove();
            break;
        case 'close-modal':
            closeModal();
            break;
        case 'new':
            newProject();
            break;
        case 'template':
            $('#new-prompt').value = { villa: 'أرض 20×25 متر، فيلا ثلاثة أدوار إجمالًا، خمس غرف نوم، مصعد، مجلس قريب من المدخل، والمعيشة على الحديقة. الشارع جنوب. تصميم حديث وخصوصية عالية.', chalet: 'شاليه 18×25 متر، دور واحد، ثلاث غرف نوم، مسبح وحديقة، المعيشة مرتبطة بالجهة الخارجية. الشارع جنوب.', office: 'مكاتب إدارية على أرض 24×30 متر، دورين، 8 مكاتب، استقبال قريب من المدخل، غرف اجتماعات وخدمات. الشارع شرق.', warehouse: 'مستودع 40×60 متر، دور واحد، منطقة تخزين رئيسية، منطقة استلام وتحميل، مكتب تشغيل وخدمات، 6 مواقف. الشارع جنوب.', retail: 'محل تجاري 20×30 متر، دور واحد، صالة عرض، مخزن خلفي، مكتب إدارة وخدمات. الشارع غرب.' }[b.dataset.template];
            $('#new-prompt').focus();
            break;
        case 'brief':
            openBrief();
            break;
        case 'design-settings': {
            const m=model(), d=m.design || {stage:'concept',projectType:'villa',priority:'balanced',style:'unspecified'};
            showModal('إعدادات التصميم المفاهيمي', `<p class="modal-lead">هذه الخيارات تغيّر طريقة المقارنة والتوصيف، ولا تعني انتقال المشروع إلى مستوى اعتماد هندسي.</p><form id="design-settings-form"><div class="brief-confirm-grid"><label class="field"><span>مرحلة العمل</span><select name="stage">${[['concept','الفكرة'],['development','تطوير المفهوم'],['review','مراجعة']].map(([v,l])=>`<option value="${v}" ${d.stage===v?'selected':''}>${l}</option>`).join('')}</select></label><label class="field"><span>أولوية المقارنة</span><select name="priority">${[['balanced','متوازن'],['privacy','خصوصية'],['outdoor','مساحات خارجية'],['compact','كفاءة ودمج']].map(([v,l])=>`<option value="${v}" ${d.priority===v?'selected':''}>${l}</option>`).join('')}</select></label><label class="field"><span>طابع العرض</span><select name="style">${[['unspecified','غير محدد'],['modern','حديث'],['classic','كلاسيكي'],['industrial','صناعي']].map(([v,l])=>`<option value="${v}" ${d.style===v?'selected':''}>${l}</option>`).join('')}</select></label></div><div class="stage-explainer"><b>الفكرة:</b> توزيع وبرنامج أولي · <b>التطوير:</b> قرارات أكثر تثبيتًا · <b>المراجعة:</b> تجهيز للتسليم والملاحظات. لا تغيّر المرحلة تلقائيًا حالة الفحوص غير المنفذة.</div><div class="modal-footer"><button class="btn primary" type="submit">حفظ الإعدادات</button></div></form>`);
            break;
        }
        case 'design-stage': {
            mutable();
            const stageName=b.dataset.stage;
            if(!['concept','development','review'].includes(stageName)) throw Error('مرحلة التصميم غير صالحة.');
            if((model().design?.stage||'concept')===stageName) break;
            const m=clone(model()); m.design={...(m.design||{}),stage:stageName}; edit(m,'مرحلة التصميم: '+({concept:'الفكرة',development:'التطوير',review:'المراجعة'}[stageName]));
            break;
        }
        case 'select':
            selectRoom(b.dataset.id);
            break;
        case 'level':
            state.levelId = b.dataset.id;
            if (!shown().levels.find(l => l.id === state.levelId)?.rooms.some(r => r.id === state.selectedId))
                state.selectedId = null;
            render();
            break;
        case 'view':
            state.view = b.dataset.view;
            render();
            break;
        case 'dimensions':
            state.dimensions = !state.dimensions;
            render();
            break;
        case 'furniture':
            state.furniture = !state.furniture;
            render();
            break;
        case 'all-floors':
            state.all = !state.all;
            render();
            break;
        case 'cutaway':
            state.cutaway = !state.cutaway;
            render();
            break;
        case 'fit':
            renderer?.reset();
            $('#plan-host').scrollTo(0, 0);
            break;
        case 'zoom-in':
            renderer?.zoom(.85);
            break;
        case 'zoom-out':
            renderer?.zoom(1.15);
            break;
        case 'mobile':
            switchMobile(b.dataset.panel);
            break;
        case 'cancel-preview':
            state.preview = null;
            render();
            $('#assistant-message').textContent = 'أُلغي الاقتراح؛ النسخة المحفوظة لم تتغير.';
            break;
        case 'resolve-preview': {
            const p = state.preview;
            if (!p) break;
            const resolved = resolvePreview(model(), p);
            if (!resolved) throw Error('لم أجد حلًا آليًا آمنًا يحافظ على العناصر المثبتة. قلّل التوسعة أو غيّر اتجاهها أو ألغِ تثبيت العنصر الذي تريد تحريكه.');
            state.preview = { ...resolved, label: p.label + ' · حل تعارض مقترح' };
            render();
            $('#assistant-message').textContent = 'اقترح مسار حلًا لا يحرّك العناصر المثبتة. ما زال التعديل معاينة فقط حتى تضغط «اعتماد التعديل».';
            break;
        }
        case 'commit-preview': {
            const p = state.preview;
            if (!p)
                break;
            if (p.newWarnings?.length && !$('#ack-warnings')?.checked)
                throw Error('راجع التنبيهات الجديدة وأكّد الاطلاع قبل الاعتماد.');
            const next = commitPreview(model(), p);
            state.preview = null;
            edit(next, p.label);
            toast('اعتُمد التعديل وحُفظت نسخة جديدة.');
            break;
        }
        case 'undo': {
            mutable();
            if (state.history.cursor === 0)
                break;
            state.undoStack.push(state.history.cursor);
            const parent = state.history.revisions[state.history.cursor].parentIndex;
            state.history.cursor = Number.isInteger(parent) ? parent : state.history.cursor - 1;
            state.history.audit.push({ type: 'undo', at: new Date().toISOString() });
            render();
            persist();
            break;
        }
        case 'redo': {
            mutable();
            if (!state.undoStack.length)
                break;
            state.history.cursor = state.undoStack.pop();
            state.history.audit.push({ type: 'redo', at: new Date().toISOString() });
            render();
            persist();
            break;
        }
        case 'lock': {
            mutable();
            const r = selected();
            if (!r)
                break;
            const m = clone(model()), target = m.levels.flatMap(l => l.rooms).find(x => x.id === r.id);
            target.locked = !target.locked;
            edit(m, target.locked ? 'تثبيت ' + r.name : 'إلغاء تثبيت ' + r.name);
            break;
        }
        case 'toggle-requirement': {
            mutable();
            const m = clone(model()), req = m.requirements.find(r => r.id === b.dataset.id);
            req.locked = !req.locked;
            edit(m, (req.locked ? 'تثبيت بند: ' : 'إلغاء تثبيت بند: ') + req.label);
            break;
        }
        case 'add-requirement':
            mutable();
            showModal('أضف بندًا لا يجب أن يُنسى', '<form id="requirement-form"><label class="field"><span>المتطلب</span><textarea name="text" rows="3" maxlength="1000" required placeholder="مثلًا: لا تطل نوافذ المجلس على الحديقة العائلية."></textarea></label><div class="notice">يُحفظ كبند يحتاج مراجعة، ولا يُوصف بأنه منفّذ أو مفحوص آليًا.</div><div class="modal-footer"><button class="btn primary" type="submit">إضافة وتثبيت البند</button></div></form>');
            break;

        case 'window': {
            mutable(); const r=selected(); if (!r) break;
            const a=effectiveAuthoring(model()), w=(r.windows||[]).find(w=>w.id===b.dataset.windowId);
            const types=a.windowTypes.map(t=>`<option value="${E(t.id)}" ${w?.typeId===t.id?'selected':''}>${E(t.name)}</option>`).join('');
            showModal('النوافذ — '+r.name, `<p class="modal-lead">تُربط النافذة بحد الغرفة والجدار المشتق. لم تُفحص متطلبات الإنارة أو التهوية أو المنتج المصنع.</p>${(r.windows||[]).map(x=>`<div class="detail-row"><span>${E(x.id)} · ${fmt(x.width)} × ${fmt(x.height)} م</span><button class="text-button" data-action="window" data-window-id="${E(x.id)}">تعديل</button><button class="text-button" data-action="remove-window" data-window-id="${E(x.id)}">حذف بمعاينة</button></div>`).join('')}<form id="window-form"><input type="hidden" name="windowId" value="${E(w?.id||'')}"><div class="properties-grid"><label class="field full"><span>النوع المفاهيمي</span><select name="typeId">${types}</select></label><label class="field"><span>جهة الاستضافة</span><select name="side">${[['north','شمال'],['south','جنوب'],['east','شرق'],['west','غرب']].map(([v,n])=>`<option value="${v}" ${w?.side===v?'selected':''}>${n}</option>`).join('')}</select></label>${[['width','العرض بالمتر',w?.width??1.2,.1,5],['height','الارتفاع بالمتر',w?.height??1.2,.1,5],['sill','ارتفاع الجلسة بالمتر',w?.sill??.9,0,5],['offset','الموضع النسبي 0–1',w?.offset??.5,0,1]].map(([k,n,v,min,max])=>`<label class="field"><span>${n}</span><input type="number" name="${k}" value="${v}" min="${min}" max="${max}" step=".01" required></label>`).join('')}</div><div class="modal-footer"><button class="btn primary" type="submit">${w?'معاينة التعديل':'معاينة إضافة نافذة'}</button></div></form>`); break;
        }
        case 'remove-window':
            mutable(); closeModal(); stage({type:'remove-window',roomId:state.selectedId,windowId:b.dataset.windowId},'حذف نافذة'); switchMobile('workspace'); break;
        case 'notch': {
            mutable();const r=selected();if(!r)break;
            showModal('تجويف زاوية — '+r.name,`<p class="modal-lead">تقص هذه العملية مساحة من زاوية محددة لتكوين مضلع L. لا يُملأ الفراغ تلقائيًا. أي باب أو نافذة يتأثر سيظهر في الفحص.</p><form id="notch-form"><div class="properties-grid"><label class="field"><span>عرض الجزء المقصوص (م)</span><input type="number" name="width" min=".1" max="${Math.max(.1,r.w-.51)}" step=".01" value=".75" required></label><label class="field"><span>عمق الجزء المقصوص (م)</span><input type="number" name="depth" min=".1" max="${Math.max(.1,r.d-.51)}" step=".01" value=".75" required></label><label class="field full"><span>زاوية القص</span><select name="corner"><option value="ne">شمال شرق</option><option value="nw">شمال غرب</option><option value="se">جنوب شرق</option><option value="sw">جنوب غرب</option></select></label></div><div class="modal-footer"><button type="submit" class="btn primary">معاينة المضلع الجديد</button></div></form>`);break;
        }
        case 'wall-types': {
            const a=effectiveAuthoring(model());
            showModal('أنواع الجدران وطبقاتها',`<p class="modal-lead">طبقات مفاهيمية مشتقة حول محور حدود المساحات؛ ليست مواصفة إنشائية. المساحات المعروضة محسوبة من الحدود وليست صافيًا مصدقًا بعد التشطيب.</p><form id="wall-types-form">${a.wallTypes.map((t,i)=>`<section class="notice"><h3>${E(t.name)}</h3><p>${t.classification==='external'?'خارجي':'داخلي'} · المجموع الحالي ${fmt(t.totalThickness*1000)} مم</p>${t.layers.map((l,j)=>`<label class="field"><span>${E(l.name)} — ${E(l.provenance||'unknown')}</span><span class="input-unit"><input name="layer-${i}-${j}" type="number" min="1" max="500" step="1" value="${round(l.thickness*1000)}" required ${state.readOnly?'disabled':''}><small>مم</small></span></label>`).join('')}</section>`).join('')}<div class="notice warn">ستتأثر جميع الجدران المرتبطة بهذه الأنواع. لا تتغير حدود الغرف أو أبوابها؛ يلزم تقييم صافي المساحات والتخصصات لاحقًا.</div><div class="modal-footer"><button class="btn primary" type="submit" ${state.readOnly?'disabled':''}>معاينة طبقات الجدران</button></div></form>`);break;
        }
        case 'confirm-ifc': {
            mutable(); if(!state.ifcCandidate) throw Error('لا توجد معاينة IFC صالحة.');
            if(state.ifcBase!==JSON.stringify(model())) throw Error('تغيّر المشروع أثناء الاستيراد؛ أعد قراءة الملف.');
            if(!$('#ifc-ack')?.checked) throw Error('أكد مراجعة حدود الاستيراد أولًا.');
            const candidate=state.ifcCandidate;state.ifcCandidate=null;
            await saveQueue;setProject(createHistory(candidate));closeModal();persist();toast('استُورد مشروع مستقل؛ لم تُحذف النسخة السابقة.');break;
        }
        case 'remove-door':
            mutable();closeModal();stage({type:'remove-door',roomId:state.selectedId,doorId:b.dataset.id},'حذف الباب المحدد فقط');break;
        case 'door': {
            mutable();const r=selected();if(!r)break;
            const d=b.dataset.new==='true'?null:(r.doors.find(x=>x.id===b.dataset.id)||r.doors[0]);
            showModal('الأبواب — '+r.name,`<p class="modal-lead">تعديل باب محدد أو إضافة باب مستقل. تبقى بقية الأبواب وهوياتها محفوظة؛ كل تغيير يُراجع قبل الاعتماد.</p><div class="suggestion-chips">${r.doors.map((x,i)=>`<button data-action="door" data-id="${E(x.id)}">باب ${i+1}${x.entry?' · مدخل':''}</button>`).join('')}<button data-action="door" data-new="true">إضافة باب</button></div><form id="door-form"><input type="hidden" name="doorId" value="${E(d?.id||'')}"><input type="hidden" name="create" value="${d?'false':'true'}"><div class="properties-grid"><label class="field full"><span>جهة الباب</span><select name="side">${[['south','جنوب'],['north','شمال'],['east','شرق'],['west','غرب']].map(([v,label])=>`<option value="${v}" ${d?.side===v?'selected':''}>${label}</option>`).join('')}</select></label><label class="field"><span>عرض الباب (م)</span><input name="width" type="number" min=".3" max="5" step=".05" value="${d?.width??.9}" required></label><label class="field"><span>ارتفاع الباب (م)</span><input name="height" type="number" min=".3" max="${r.height}" step=".05" value="${d?.height??2.15}" required></label><label class="field full"><span>موضعه النسبي (0–1)</span><input name="offset" type="number" min="0" max="1" step=".05" value="${d?.offset??.5}" required></label></div><label class="check-line"><input name="entry" type="checkbox" ${d?.entry?'checked':''}><span>مدخل خارجي؛ سيُفحص وجوده على حد مفتوح.</span></label><div class="notice warn">الفتحات يجب أن تلائم جدارًا مضيفًا واحدًا. فحص الوصول مفاهيمي، وليس اعتماد حريق أو إتاحة.</div><div class="modal-footer">${d?`<button class="btn danger" type="button" data-action="remove-door" data-id="${E(d.id)}">معاينة حذف هذا الباب</button>`:''}<button class="btn primary" type="submit">معاينة موضع الباب</button></div></form>`);break;
        }
        case 'near-entry':
            mutable();
            stage({type:'near',roomId:state.selectedId,target:'entry'},'تقريب '+selected().name+' من المدخل');
            switchMobile('workspace');
            break;
        case 'near-garden':
            mutable();
            stage({type:'near',roomId:state.selectedId,target:'garden'},'تقريب '+selected().name+' من الجهة الخارجية');
            switchMobile('workspace');
            break;
        case 'swap': {
            mutable();
            const r = selected();
            if (!r)
                break;
            const l = model().levels.find(l => l.rooms.some(s => s.id === r.id));
            showModal('مبادلة موقع ' + r.name, `<form id="swap-form"><label class="field"><span>المساحة الثانية</span><select name="targetId">${l.rooms.filter(s => s.id !== r.id && !s.locked && !['hall', 'stairs'].includes(s.kind)).map(s => `<option value="${E(s.id)}">${E(s.name)} — ${fmt(area(s))} م²</option>`).join('')}</select></label><div class="notice">تُبدّل المساحتان مواضعهما وأبعادهما، وتحافظ كل منهما على اسمها وتعليقاتها. تُعاين فروق الأبعاد قبل الاعتماد.</div><div class="modal-footer"><button class="btn primary" type="submit">معاينة المبادلة</button></div></form>`);
            break;
        }
        case 'suggest':
            $('#command-input').value = b.dataset.text;
            $('#command-input').focus();
            break;
        case 'command-help':
            showModal('أوامر تعديل موضعية ومفهومة', `<p class="modal-lead">يمكنك ذكر اسم المساحة أو تحديدها من المخطط. كل أمر ينتج معاينة أثر قبل أي اعتماد.</p><div class="original-prompt">انقل المجلس قرب المدخل
وسع المعيشة متر باتجاه الحديقة
خلي المطبخ قرب الحديقة
العرض 5
العمق 4
أبعاد 5×4
انقل 1 متر شمال
الباب جنوب
سم المعيشة العائلية
بادل مع غرفة الطعام</div><div class="notice">المحلل المحلي حتمي ومحدود النطاق: إن لم يفهم الأمر يرفضه. الذكاء السحابي اختياري، وحتى عند استخدامه لا يملك صلاحية الاعتماد أو تجاوز الأقفال.</div>`);
            break;
        case 'ai-mode':
            if (state.ai) {
                state.ai = false;
                render();
                break;
            }
            if (!api.aiConfigured) {
                showModal('المحلل المحلي جاهز؛ الذكاء السحابي غير مربوط', `<p class="modal-lead">هذه النسخة لا تدّعي فهمًا حرًا بالذكاء الاصطناعي دون مزوّد فعلي. الأوامر المحلية والحقول المباشرة تعمل دون مفتاح.</p><div class="notice">يدعم الخادم ربط Claude بإعدادَي <code>ANTHROPIC_API_KEY</code> و<code>ANTHROPIC_MODEL</code>. تُحفظ الأسرار على الخادم فقط. الربط الفعلي يحتاج مفتاحًا صالحًا، ولم يُختبر هنا باستدعاء مدفوع.</div>`);
                break;
            }
            if (!api.user) {
                await account();
                break;
            }
            showModal('تفعيل اقتراحات الذكاء السحابي', `<p class="modal-lead">عند الإرسال، سيُرسل الأمر وبيانات الغرفة المحددة وأسماء ومعرّفات المساحات إلى Anthropic. لن يُرسل سجل النسخ أو تعليقاتك. قد تنطبق رسوم المزود وسياسة احتفاظه.</p><div class="notice">كل اقتراح يمر بالفحص والمعاينة. لا يستطيع المزود حفظ التعديل تلقائيًا أو تجاوز القفل.</div><div class="modal-footer"><button class="btn light" data-action="close-modal">إلغاء</button><button class="btn primary" data-action="enable-ai">أوافق على تفعيل الإرسال</button></div>`);
            break;
        case 'enable-ai':
            state.ai = true;
            closeModal();
            render();
            break;
        case 'projects':
            await projects();
            break;
        case 'fork-project': {
            mutable();await saveQueue;const copy=clone(model());copy.id=uid();copy.title=(copy.title+' — نسخة مستقلة').slice(0,120);setProject(createHistory(copy));closeModal();await persist();toast('أنشئت نسخة مستقلة؛ بقي المشروع السابق محفوظًا.');break;
        }
        case 'open-local': {
            await saveQueue;
            const h = await loadLocal(b.dataset.id);
            for(const [k,v] of Object.entries(await loadLocalVersions(b.dataset.id)))state.versions.set(k,v);
            setProject(h);
            closeModal();
            saveStatus('مشروع مستعاد من هذا الجهاز');
            switchMobile('workspace');
            break;
        }
        case 'delete-local':
            showModal('حذف المشروع من هذا الجهاز؟', `<p class="modal-lead">سيُحذف سجل المشروع المحلي. النسخة على الخادم، إن وجدت، لن تُحذف. صدّر ملف JSON قبل الحذف للاحتفاظ بنسخة.</p><div class="modal-footer"><button class="btn light" data-action="close-modal">إلغاء</button><button class="btn danger" data-action="confirm-delete-local" data-id="${E(b.dataset.id)}">حذف النسخة المحلية</button></div>`);
            break;
        case 'confirm-delete-local':
            if (b.dataset.id === model().id)
                throw Error('افتح مشروعًا آخر أولًا حتى لا يعاد حفظ المشروع المفتوح بعد حذفه.');
            await deleteLocal(b.dataset.id);
            await projects();
            break;
        case 'save-cloud':
            await saveCloud();
            if (api.user)
                closeModal();
            break;
        case 'open-cloud': {
            await saveQueue;
            const data = await api.request('/api/projects/' + encodeURIComponent(b.dataset.id));
            setProject(assertHistory(data.history));
            state.versions.set(api.user.id + ':' + b.dataset.id, data.version);
            closeModal();
            persist();
            toast('استُعيد المشروع من حسابك، وحُفظ محليًا.');
            break;
        }
        case 'render-center':
            await openRenderStudio({api,getModel:model,getRevision:()=>state.history.revisions[state.history.cursor].id,getCloudVersion:()=>state.versions.get(api.user.id+':'+model().id),isPending:()=>!!state.preview,isReadOnly:()=>state.readOnly,saveCloud,showModal,onSelect:selectRoom,reportError});
            break;
        case 'account':
            await account();
            break;
        case 'auth-mode':
            await account(b.dataset.mode);
            break;
        case 'change-password':
            showModal('تغيير كلمة المرور', `<form id="password-form"><label class="field"><span>كلمة المرور الحالية</span><input name="currentPassword" type="password" required maxlength="200" autocomplete="current-password"></label><label class="field"><span>كلمة المرور الجديدة</span><input name="newPassword" type="password" required minlength="12" maxlength="200" autocomplete="new-password"></label><div class="modal-footer"><button class="btn primary" type="submit">تغيير كلمة المرور</button></div></form>`);
            break;
        case 'delete-account':
            showModal('حذف الحساب نهائيًا', `<p class="notice error">سيُحذف حسابك ومشاريعك وروابط المشاركة المحفوظة على هذا الخادم. المشاريع المحلية في هذا المتصفح لا تُحذف تلقائيًا.</p><form id="delete-account-form"><label class="field"><span>أدخل كلمة المرور للتأكيد</span><input name="password" type="password" required maxlength="200" autocomplete="current-password"></label><label class="check-line"><input name="confirmDelete" type="checkbox" required><span>أفهم أن حذف بيانات الحساب على الخادم نهائي.</span></label><div class="modal-footer"><button class="btn danger" type="submit">حذف الحساب والبيانات</button></div></form>`);
            break;
        case 'logout':
            await api.logout();
            state.versions.clear();
            state.ai = false;
            closeModal();
            render();
            toast('سُجّل الخروج. الملفات المحلية تظل على هذا المتصفح.');
            break;
        case 'share':
            await share();
            break;
        case 'revoke-share':
            await api.request('/api/shares/' + encodeURIComponent(b.dataset.id), { method: 'DELETE', body: {} });
            toast('أُلغي رابط المراجعة.');
            await share();
            break;
        case 'copy-share':
            await navigator.clipboard.writeText($('#shared-url').value);
            toast('نُسخ الرابط.');
            break;
        case 'measure':
            state.measurement.active = !state.measurement.active;
            if (!state.measurement.active) state.measurement = {active:false,a:null,b:null};
            else state.measurement = {active:true,a:null,b:null};
            render();
            break;
        case 'history':
            openHistory();
            break;
        case 'compare-revisions':
            revisionCompareForm();
            break;
        case 'restore': {
            mutable();
            const index = Number(b.dataset.index), past = state.history.revisions[index];
            if (!past)
                break;
            edit(clone(past.model), 'استعادة: ' + past.label);
            closeModal();
            toast('استُعيدت النسخة في إصدار جديد.');
            break;
        }
        case 'name-revision':
            mutable();
            showModal('نسخة تحمل اسم قرارك', '<form id="revision-form"><label class="field"><span>اسم النسخة</span><input name="label" maxlength="100" required placeholder="مثلًا: توزيع معتمد للمراجعة الأولى"></label><div class="modal-footer"><button class="btn primary" type="submit">حفظ نسخة مسماة</button></div></form>');
            break;
        case 'rename-project':
            mutable();
            showModal('اسم المشروع', `<form id="rename-form"><label class="field"><span>اسم المشروع</span><input name="title" value="${E(model().title)}" maxlength="120" required></label><div class="modal-footer"><button class="btn primary" type="submit">حفظ الاسم</button></div></form>`);
            break;
        case 'issues':
            openIssues();
            break;
        case 'model-health':
            openModelHealth();
            break;
        case 'building-elements':
            buildingElements();
            break;
        case 'requirements-center':
            requirementsCenter();
            break;
        case 'focus-issue':
            if (b.dataset.id) {
                selectRoom(b.dataset.id);
                closeModal();
                switchMobile('workspace');
            }
            break;
        case 'alternatives':
            openAlternatives();
            break;
        case 'use-alternative': {
            const a = state.alternatives[Number(b.dataset.index)];
            if (!a)
                break;
            const issues = validate(a.model), existing = new Set(validate(model()).filter(i => i.status === 'error').map(i => i.id));
            state.preview = { candidate: clone(a.model), changes: diffModels(model(), a.model), issues, blockers: issues.filter(i => i.status === 'error'), impact: impactSummary(model(), a.model), base: JSON.stringify(model()), label: a.label };
            closeModal();
            render();
            switchMobile('workspace');
            break;
        }
        case 'comments':
            await comments();
            break;
        case 'review-center':
            await reviewCenter();
            break;
        case 'resolve-review-comment':
            await api.request('/api/review-comments/'+encodeURIComponent(b.dataset.id),{method:'POST',body:{resolved:b.dataset.resolved==='true'}});
            await reviewCenter();
            break;
        case 'resolve-comment': {
            mutable();
            const m = clone(model()), c = m.comments.find(c => c.id === b.dataset.id);
            c.resolved = !c.resolved;
            edit(m, c.resolved ? 'إغلاق تعليق' : 'إعادة فتح تعليق');
            comments();
            break;
        }
        case 'export':
            exportMenu();
            break;
        case 'download': {
            const kind = b.dataset.kind, name = 'masar-' + model().id.slice(0, 8);
            if (state.preview && kind === 'png')
                throw Error('ألغِ المعاينة أو اعتمدها قبل تنزيل لقطة المجسم.');
            if (kind === 'json')
                download(name + '.json', JSON.stringify(exportEnvelope(state.history), null, 2), 'application/json');
            if (kind === 'svg')
                download(name + '-' + state.levelId + '.svg', planSVG(model(), state.levelId, { dimensions: true, furniture: state.furniture, interactive: false }), 'image/svg+xml');
            if (kind === 'dxf')
                download(name + '-' + state.levelId + '.dxf', exportDXF(model(), state.levelId), 'application/dxf');
            if (kind === 'ifc')
                download(name + '.ifc', exportIFC(model()), 'application/x-step');
            if (kind === 'obj')
                download(name + '.obj', exportOBJ(model()), 'text/plain');
            if (kind === 'csv')
                download(name + '-rooms.csv', roomScheduleCSV(), 'text/csv;charset=utf-8');
            if (kind === 'elements')
                download(name + '-building-elements.csv', elementScheduleCSV(model()), 'text/csv;charset=utf-8');
            if (kind === 'requirements')
                download(name + '-requirements.csv', requirementMatrixCSV(model()), 'text/csv;charset=utf-8');
            if (kind === 'rules')
                download(name + '-concept-quality.json', JSON.stringify(evaluateRulePack(model()), null, 2), 'application/json');
            if (kind === 'report')
                download(name + '-report.html', reportHTML(), 'text/html');
            if (kind === 'png') {
                if (!renderer)
                    throw Error('العرض ثلاثي الأبعاد غير متاح.');
                renderer.draw();
                const source = $('#scene'), canvas = document.createElement('canvas');
                canvas.width = source.width;
                canvas.height = source.height + 65;
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#f2f5eb';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(source, 0, 0);
                ctx.fillStyle = '#64745a';
                ctx.font = '15px Tahoma';
                ctx.textAlign = 'center';
                ctx.fillText('MASAR — CONCEPTUAL VISUALIZATION / NOT FOR CONSTRUCTION', canvas.width / 2, canvas.height - 24);
                canvas.toBlob(blob => { if (blob)
                    download(name + '.png', blob, 'image/png');
                else
                    reportError(Error('تعذّر تجهيز اللقطة.')); });
            }
            break;
        }
        case 'import':
            mutable();
            $('#import-input').value = '';
            $('#import-input').click();
            break;
        case 'confirm-dxf': break;
        case 'about':
            showModal('قدرات مسار وحدوده الصريحة', `<p class="modal-lead">MASAR 3 يبني نموذجًا مفاهيميًا موحدًا، ثم يشتق منه طبقة عناصر مبنى قابلة للتسليم والتنسيق دون تغيير مصدر الحقيقة.</p><div class="notice"><strong>متاح الآن:</strong> فيلا وشاليه ومكاتب ومستودع وتجزئة؛ 1–8 أدوار؛ مصعد ومسبح كعناصر مفاهيمية؛ متطلبات قابلة للقياس مثل قرب المجلس من المدخل؛ تعديل علائقي واتجاهي؛ معاينة أثر؛ أقفال؛ بدائل محسوبة؛ تراجع/إعادة؛ تعليقات داخلية وملاحظات مراجعين عبر الرابط؛ قياس مباشر؛ مقارنة نسختين؛ حفظ محلي وخادمي؛ مشاركة ثابتة؛ استيراد DXF مرجعي؛ طبقة مبنى مشتقة للجدران/الأبواب/البلاطات/السقف مع جداول عناصر ومتطلبات؛ حزمة جودة مفاهيمية قابلة للإصدار؛ وتصدير JSON/SVG/DXF/IFC4 التنسيقي/OBJ/CSV/PNG/HTML.</div><div class="notice warn"><strong>ليست مكتملة كقدرات تنفيذية:</strong> تحويل صورة أو PDF/DWG إلى BIM موثوق، استيراد IFC وround-trip BIM كامل، تصميم تفصيلي للسلالم والمصاعد والمسابح، إنشائي، MEP، حريق، إتاحة، أو اعتماد أنظمة البناء. هذه تظهر «لم تُفحص» ولا تُخفى خلف درجة جودة.</div><div class="notice">المحرك المحلي يعمل بلا CDN. الذكاء السحابي اختياري ومقيد بالاقتراح فقط. الحفظ المحلي ليس Backup سحابيًا، والحفظ/المشاركة على الحساب يحتاجان الخادم.</div><p class="modal-lead">نطاق المولّد: أرض 12–120 م عرضًا و15–160 م عمقًا، حتى 8 أدوار، حتى 16 غرفة نوم سكنية أو 20 مكتبًا في برنامج المكاتب، بحد أقصى 200 مساحة و100 نسخة للمشروع.</p>`);
            break;
        default: break;
    }
}
async function handleForm(form) {
    const data = new FormData(form), get = k => String(data.get(k) || '').trim();
    switch (form.id) {
        case 'new-form':
            confirmBrief(understand(get('prompt') || $('#new-prompt').value));
            break;
        case 'brief-form': {
            mutable();
            const brief = clone(state.pendingBrief);
            for (const k of ['width','depth','floors','bedrooms','offices','parking']) { brief[k]=Number(data.get(k)); brief.sources[k]='confirmed'; }
            brief.title=get('title'); brief.street=get('street'); brief.projectType=get('projectType'); brief.priority=get('priority'); brief.style=get('style'); brief.elevator=data.has('elevator'); brief.pool=data.has('pool');
            brief.sources.street='confirmed'; brief.sources.projectType='confirmed';
            if(!brief.title) throw Error('اسم المشروع مطلوب.');
            if(!['villa','chalet','office','warehouse','retail'].includes(brief.projectType)) throw Error('نوع المشروع غير مدعوم.');
            if(!Number.isInteger(brief.floors)||brief.floors<1||brief.floors>8) throw Error('عدد الأدوار يجب أن يكون بين 1 و8.');
            if(['villa','chalet'].includes(brief.projectType)&&(!Number.isInteger(brief.bedrooms)||brief.bedrooms<1||brief.bedrooms>16)) throw Error('المشروع السكني يحتاج من 1 إلى 16 غرفة نوم ضمن نطاق المولّد.');
            if(brief.projectType==='office'&&(!Number.isInteger(brief.offices)||brief.offices<1||brief.offices>20)) throw Error('برنامج المكاتب يدعم من مكتب واحد إلى 20 مكتبًا.');
            if(!Number.isInteger(brief.parking)||brief.parking<0||brief.parking>30) throw Error('عدد المواقف يجب أن يكون بين 0 و30.');
            if(!Number.isFinite(brief.width)||brief.width<12||brief.width>120||!Number.isFinite(brief.depth)||brief.depth<15||brief.depth>160) throw Error('نطاق الأرض المدعوم: عرض 12–120 م وعمق 15–160 م.');
            brief.buildingAreaMin=get('buildingAreaMin')?Number(data.get('buildingAreaMin')):null;
            brief.buildingAreaMax=get('buildingAreaMax')?Number(data.get('buildingAreaMax')):null;
            if((brief.buildingAreaMin===null)!==(brief.buildingAreaMax===null))throw Error('أدخل الحدين الأدنى والأعلى لمساحة البناء، أو اتركهما معًا فارغين.');
            brief.unresolved=[];
            const m=generate(brief);
            m.requirements.push({id:uid(),label:'أي تفاصيل نصية لم تتحول إلى متطلب قابل للقياس تبقى ضمن الطلب الأصلي وتحتاج مراجعة معمارية بشرية.',type:'custom',source:'requested',locked:true});
            const errors=validate(m).filter(i=>i.status==='error');
            if(errors.length) throw Error('لم ينتج توزيع متصل وصالح هندسيًا داخل نموذج مسار: '+errors[0].message);
            await saveQueue; setProject(createHistory(m)); closeModal(); switchMobile('workspace'); persist();
            toast('أُنشئ المفهوم الأول. راجع العلاقات والمؤشرات ثم ثبّت القرارات المهمة.');
            break;
        }
        case 'design-settings-form': {
            mutable();
            const stageName=get('stage'), priority=get('priority'), style=get('style');
            if(!['concept','development','review'].includes(stageName)||!['balanced','privacy','outdoor','compact'].includes(priority)||!['unspecified','modern','classic','industrial'].includes(style)) throw Error('إعدادات التصميم غير صالحة.');
            const m=clone(model()); m.design={...(m.design||{}),stage:stageName,priority,style};
            if(JSON.stringify(m.design)===JSON.stringify(model().design)) { closeModal(); toast('لم تتغير إعدادات التصميم.'); break; }
            edit(m,'تحديث إعدادات التصميم'); closeModal();
            break;
        }
        case 'properties-form': {
            mutable();
            const r = selected();
            if (!r)
                throw Error('اختر مساحة.');
            const name = get('name'), m = clone(model()), target = m.levels.flatMap(l => l.rooms).find(x => x.id === r.id);
            if (!name)
                throw Error('اسم المساحة مطلوب.');
            target.name = name;
            for (const k of ['w', 'd', 'x', 'y'])
                if (data.has(k)) {
                    const v = Number(data.get(k));
                    if (!Number.isFinite(v))
                        throw Error('أدخل رقمًا صالحًا.');
                    target[k] = round(v);
                }
            assertModel(m);
            checkLocks(model(), m);
            const changes = diffModels(model(), m);
            if (!changes.length) {
                toast('لم تتغيّر أي قيمة.');
                break;
            }
            const issues = validate(m);
            state.preview = { candidate: m, changes, issues, blockers: issues.filter(i => i.status === 'error'), base: JSON.stringify(model()), label: 'تعديل ' + r.name };
            render();
            switchMobile('workspace');
            break;
        }
        case 'command-form': {
            mutable();
            const text = $('#command-input').value.trim();
            if (!text)
                throw Error('اكتب أمر التعديل أولًا.');
            $('#assistant-message').classList.remove('error');
            $('#assistant-message').textContent = state.ai ? 'جارٍ طلب اقتراح من المزود…' : 'جارٍ تحليل الأمر محليًا…';
            let command;
            if (state.ai) {
                const base = JSON.stringify(model());
                const result = await api.request('/api/ai/propose', { method: 'POST', body: { model: model(), roomId: state.selectedId, text, consent: true } });
                if (base !== JSON.stringify(model()))
                    throw Error('تغيّر المشروع أثناء الطلب؛ أعد المحاولة على النسخة الجديدة.');
                command = result.command;
            }
            else
                command = parseCommand(text, model(), state.selectedId);
            stage(command, 'أمر: ' + text.slice(0, 80));
            switchMobile('workspace');
            break;
        }

        case 'window-form': {
            mutable();const cmd={type:'window',roomId:state.selectedId,side:get('side'),typeId:get('typeId'),width:Number(data.get('width')),height:Number(data.get('height')),sill:Number(data.get('sill')),offset:Number(data.get('offset'))};
            if(get('windowId'))cmd.windowId=get('windowId');closeModal();stage(cmd,'تعديل نافذة');switchMobile('workspace');break;
        }
        case 'notch-form': {
            mutable();const cmd={type:'notch',roomId:state.selectedId,width:Number(data.get('width')),depth:Number(data.get('depth')),corner:get('corner')};closeModal();stage(cmd,'تجويف زاوية');switchMobile('workspace');break;
        }
        case 'wall-types-form': {
            mutable();const m=clone(model());m.authoring=clone(effectiveAuthoring(m));
            for(const [i,t] of m.authoring.wallTypes.entries()) {for(const [j,l] of t.layers.entries()){const mm=Number(data.get(`layer-${i}-${j}`));if(!Number.isFinite(mm)||mm<1||mm>500)throw Error('أدخل سمكًا صالحًا بالملليمتر.');l.thickness=round(mm/1000);l.provenance='user-concept-assumption';}t.totalThickness=round(t.layers.reduce((n,l)=>n+l.thickness,0));t.provenance='user-concept-type-not-engineering-spec';}
            assertModel(m);checkLocks(model(),m);const changes=diffModels(model(),m);if(!changes.length){toast('لم تتغير الطبقات.');break;}const issues=validate(m);
            state.preview={candidate:m,changes,issues,blockers:issues.filter(i=>i.status==='error'),base:JSON.stringify(model()),label:'تغيير طبقات الجدران — كل الجدران المشتقة متأثرة'};closeModal();render();break;
        }
        case 'door-form': {
            const command = { type: 'door', roomId: state.selectedId, side: get('side'), width: Number(data.get('width')), height:Number(data.get('height')),offset: Number(data.get('offset')), entry: data.has('entry'),doorId:get('doorId')||undefined,create:get('create')==='true' };
            closeModal();
            stage(command, 'تغيير باب ' + selected().name);
            switchMobile('workspace');
            break;
        }
        case 'swap-form': {
            const command = { type: 'swap', roomId: state.selectedId, targetId: get('targetId') };
            closeModal();
            stage(command, 'مبادلة المساحات');
            switchMobile('workspace');
            break;
        }
        case 'rename-form': {
            const m = clone(model());
            m.title = get('title');
            edit(m, 'تسمية المشروع');
            closeModal();
            break;
        }
        case 'compare-form': {
            revisionComparison(Number(data.get('before')), Number(data.get('after')));
            break;
        }
        case 'revision-form': {
            edit(clone(model()), get('label'));
            closeModal();
            toast('حُفظت النسخة المسماة.');
            break;
        }
        case 'requirement-form': {
            const m = clone(model());
            m.requirements.push({ id: uid(), type: 'custom', label: get('text'), source: 'requested', locked: true });
            edit(m, 'إضافة متطلب');
            closeModal();
            break;
        }
        case 'comment-form': {
            const m = clone(model());
            if (!get('text'))
                throw Error('اكتب تعليقًا.');
            m.comments.push({ id: uid(), roomId: state.selectedId, text: get('text'), author: api.user?.name || 'مالك المشروع', at: new Date().toISOString(), resolved: false });
            edit(m, 'تعليق على ' + selected().name);
            await comments();
            break;
        }
        case 'review-comment-form': {
            if(!state.readOnly||!state.shareToken) throw Error('هذا النموذج متاح داخل رابط مراجعة فقط.');
            await api.request('/api/shares/'+encodeURIComponent(state.shareToken)+'/comments',{method:'POST',body:{author:get('author'),text:get('text'),targetId:get('targetId')}});
            toast('أُرسلت ملاحظتك إلى مالك المشروع دون تغيير التصميم.');
            await comments();
            break;
        }
        case 'password-form': {
            await api.request('/api/auth/change-password', {method:'POST',body:{currentPassword:String(data.get('currentPassword')||''),newPassword:String(data.get('newPassword')||'')}});
            closeModal(); toast('تغيّرت كلمة المرور. أُغلقت الجلسات الأخرى للحساب.');
            break;
        }
        case 'delete-account-form': {
            if(!data.has('confirmDelete')) throw Error('تأكيد الحذف مطلوب.');
            await api.request('/api/auth/account', {method:'DELETE',body:{password:String(data.get('password')||'')}});
            api.user=null; api.csrf=null; state.versions.clear(); state.ai=false; closeModal(); render(); toast('حُذف الحساب وبياناته من الخادم. المشاريع المحلية بقيت على هذا المتصفح.');
            break;
        }
        case 'auth-form': {
            try {
                await api.authenticate(state.authMode, { name: get('name'), email: get('email'), password: String(data.get('password') || '') });
                state.versions.clear();
                try{for(const [k,v] of Object.entries(await loadLocalVersions(model().id)))state.versions.set(k,v);}catch{/* A failed local store must not prevent authentication. */}
                closeModal();
                render();
                toast('أهلًا بك. الحفظ على الخادم يتم بطلبك من «مشاريعي».');
            }
            catch (e) {
                $('#auth-error').className = 'notice error';
                $('#auth-error').textContent = e.message;
            }
            break;
        }
        case 'share-form': {
            mutable();
            if (!data.has('consent'))
                throw Error('الموافقة على المشاركة مطلوبة.');
            const source = clone(model());
            await saveCloud();
            const m = clone(source);
            if (!data.has('includeComments'))
                m.comments = [];
            if (!data.has('includePrompt')) {
                m.brief.prompt = 'الوصف الأصلي غير مشمول في رابط المراجعة.';
                m.requirements = m.requirements.filter(r => !['custom', 'unresolved'].includes(r.type));
                m.brief.unresolved = [];
            }
            m.references = [];
            const result = await api.request('/api/shares', { method: 'POST', body: { model: m, days: Number(data.get('days') || 7) } });
            $('#share-result').innerHTML = `<div class="notice">الرابط صالح حتى ${E(new Date(result.expires).toLocaleString('ar-SA'))}. يعرض هذه النسخة فقط.</div><input id="shared-url" class="share-url" readonly value="${E(result.url)}" aria-label="رابط المراجعة"><div class="modal-footer"><button class="btn primary" data-action="copy-share">نسخ الرابط</button></div>`;
            break;
        }
        case 'dxf-form': {
            mutable();
            const scale = Number(data.get('scale'));
            const lines = parseDXF(state.dxfText, scale), m = clone(model());
            if (m.references.length >= 5)
                throw Error('الحد الأقصى خمسة مراجع رسم.');
            m.references.push({ type: 'dxf', name: state.dxfName, scale: 1, lines });
            edit(m, 'إضافة مرجع DXF');
            state.dxfText = null;
            closeModal();
            toast('أُضيف الرسم كمرجع خطوط؛ لم يتحول إلى جدران أو غرف.');
            break;
        }
        default: break;
    }
}
if ('serviceWorker' in navigator && !globalThis.MASAR_STANDALONE && /^https?:$/.test(location.protocol)) navigator.serviceWorker.register('/public/sw.js',{scope:'/'}).catch(() => {});
// Delegated handlers keep interactions stable after rendering and avoid inline JavaScript.
document.addEventListener('click', async (e) => { const b = e.target.closest('button[data-action]'); if (b) {
    if (b.disabled)
        return;
    try {
        await handleAction(b);
    }
    catch (err) {
        reportError(err);
    }
    return;
} const room = e.target.closest('[data-room-id]'); if (room && !state.measurement.active && Date.now() > ignoreClickUntil)
    selectRoom(room.dataset.roomId); });
document.addEventListener('invalid',e=>{
    if(e.target.closest('#modal')){const name=e.target.closest('label')?.querySelector('span')?.textContent||'القيم المطلوبة';reportError(Error('راجع '+name+'؛ أدخل قيمة ضمن النطاق المعروض وأكّد المراجعة.'));}
},true);
document.addEventListener('change',e=>{
    if(!e.target.matches('#brief-form select[name="projectType"]'))return;
    const form=e.target.form,type=e.target.value,residential=['villa','chalet'].includes(type),beds=form.elements.bedrooms,offices=form.elements.offices;
    beds.min=residential?'1':'0';offices.min=type==='office'?'1':'0';
    // A derived zero is not a residential choice. Re-read the original numeric request.
    if(residential&&Number(beds.value)===0){const original=state.pendingBrief.prompt;const parsed=understand(type==='chalet'?'شاليه، '+original:'فيلا، '+original);beds.value=String(parsed.bedrooms||3);}
    if(type==='office'&&Number(offices.value)===0)offices.value='4';
});
document.addEventListener('submit', async (e) => { e.preventDefault(); const form = e.target; if (!(form instanceof HTMLFormElement))
    return; const submit = form.querySelector('[type="submit"]'); if (submit?.disabled)
    return; if (submit)
    submit.disabled = true; try {
    await handleForm(form);
}
catch (err) {
    if (form.id === 'command-form') {
        $('#assistant-message').textContent = err.message;
        $('#assistant-message').classList.add('error');
    }
    reportError(err);
}
finally {
    if (submit?.isConnected)
        submit.disabled = false;
} });
document.addEventListener('keydown', e => { if (e.target.closest('input,textarea,select'))
    return; if (e.target.closest('[data-room-id]') && ['Enter', ' '].includes(e.key)) {
    e.preventDefault();
    selectRoom(e.target.closest('[data-room-id]').dataset.roomId);
} if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !$('#modal').open) {
    e.preventDefault();
    const b = $(`[data-action="${e.shiftKey ? 'redo' : 'undo'}"]`);
    if (!b.disabled)
        handleAction(b).catch(reportError);
} });
window.addEventListener('beforeunload', e => { if (state.dirty && !state.readOnly) {
    e.preventDefault();
    e.returnValue = '';
} });
window.addEventListener('resize', () => renderer?.draw());
$('#modal').addEventListener('click', e => { if (e.target === $('#modal')) {
    const r = $('#modal').getBoundingClientRect();
    if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom)
        closeModal();
} });
$('#import-input').addEventListener('change', async (e) => { const file = e.target.files?.[0]; if (!file)
    return; try {
    mutable();
    if (file.size > 8000000)
        throw Error('الحد الأقصى للملف 8 ميجابايت.');
    const name = file.name.toLowerCase();
    if (name.endsWith('.json')) {
        const h = importEnvelope(await file.text());
        await saveQueue;
        setProject(h);
        closeModal();
        persist();
        toast('استُعيد المشروع وسجل نسخه من الملف.');
    }
    else if (name.endsWith('.ifc')) {
        if(file.size>8000000)throw Error('الحد الأقصى 8 ميجابايت.');
        const candidate=parseIFC(await file.text());state.ifcCandidate=candidate;state.ifcBase=JSON.stringify(model());
        const counts=deriveBuildingGraph(candidate).counts,issues=validate(candidate),errors=issues.filter(x=>x.status==='error');
        showModal('معاينة IFC — لم يُستبدل مشروعك',`<p class="modal-lead">استيراد مجموعة IFC4 مدعومة إلى مشروع مستقل. سيتم الاحتفاظ بالأصل المحفوظ. لا يُستعاد منه تاريخ MASAR أو المتطلبات أو التشطيبات غير المدعومة.</p><div class="impact-grid"><div><span>الأدوار</span><strong>${candidate.levels.length}</strong></div><div><span>المساحات</span><strong>${counts.spaces}</strong></div><div><span>فتحات مدعومة</span><strong>${counts.openings}</strong></div></div><div class="notice warn">${E(candidate.brief.unresolved.join(' '))}</div><div class="notice">${errors.length?`يوجد ${errors.length} خطأ مفاهيمي يحتاج إصلاحًا. الاستيراد لا يعني قبوله هندسيًا.`:'لم يظهر خطأ مانع في فحص النموذج المفاهيمي؛ التخصصات لم تُفحص.'}</div><label class="check-line"><input id="ifc-ack" type="checkbox"><span>راجعت نطاق الاستيراد وسأتحقق من الهندسة والأبعاد والعلاقات.</span></label><div class="modal-footer"><button class="btn light" data-action="close-modal">إلغاء</button><button class="btn primary" data-action="confirm-ifc">إنشاء المشروع المستورد</button></div>`);
    }
    else if (name.endsWith('.dxf')) {
        if (file.size > 2000000)
            throw Error('الحد الأقصى لمرجع DXF هو 2 ميجابايت.');
        state.dxfText = await file.text();
        state.dxfName = file.name.slice(0, 150);
        showModal('تحديد وحدة ملف DXF', `<p class="modal-lead">استيراد خطوط LINE وLWPOLYLINE فقط كمرجع مسقط. لا تُستخرج غرف أو جدران BIM من الرسم، ولا يُفترض مقياس تلقائي.</p><form id="dxf-form"><label class="field"><span>كم مترًا تمثل وحدة واحدة في الملف؟</span><select name="scale"><option value="1">1 متر — ملف بوحدة المتر</option><option value="0.001">0.001 متر — ملف بالملليمتر</option><option value="0.01">0.01 متر — ملف بالسنتيمتر</option><option value="0.3048">0.3048 متر — ملف بالقدم</option></select></label><label class="check-line"><input type="checkbox" required><span>تحققت من وحدة ملفي. الرسم مرجع فقط، وليس هندسة معتمدة.</span></label><div class="modal-footer"><button class="btn primary" type="submit">إضافة المرجع</button></div></form>`);
    }
    else if (['image/png', 'image/jpeg'].includes(file.type)) {
        const head = new Uint8Array(await file.slice(0, 12).arrayBuffer());
        const png = head[0] === 137 && head[1] === 80 && head[2] === 78 && head[3] === 71, jpg = head[0] === 255 && head[1] === 216;
        if (!(png || jpg))
            throw Error('محتوى الصورة لا يطابق PNG أو JPEG.');
        if (state.imageRef)
            URL.revokeObjectURL(state.imageRef);
        state.imageRef = URL.createObjectURL(file);
        showModal('مرجع بصري — لا استخراج هندسي', `<p class="modal-lead">الصورة مرجع أثناء هذه الجلسة فقط. لم نُنشئ منها غرفًا أو أبعادًا، ولا تُرسل إلى مزوّد أو تُحفظ داخل مشروع JSON.</p><img class="photo-reference" src="${E(state.imageRef)}" alt="مرجع المخطط المرفوع"><div class="notice">أدخل الأبعاد بنفسك أو استورد مشروع JSON. التحويل التلقائي من الصور إلى BIM غير مدعوم؛ استيراد IFC4 متاح ضمن النطاق المعلن.</div>`);
    }
    else
        throw Error('الملفات المدعومة: مشروع JSON أو IFC4 مدعوم، مرجع DXF، وصور PNG/JPEG.');
}
catch (err) {
    reportError(err);
} });
// Measurement is transient session state. It never changes the canonical model or history.
$('#plan-host').addEventListener('click', e => {
    if (!state.measurement.active) return;
    e.preventDefault(); e.stopPropagation();
    const svg=$('#plan-host svg'); if(!svg) return;
    const pt=svg.createSVGPoint(); pt.x=e.clientX; pt.y=e.clientY;
    const p=pt.matrixTransform(svg.getScreenCTM().inverse()), m=shown();
    const point={x:round(Math.max(0,Math.min(m.site.width,p.x))),y:round(Math.max(0,Math.min(m.site.depth,m.site.depth-p.y)))};
    if (!state.measurement.a || state.measurement.b) state.measurement={active:true,a:point,b:null};
    else state.measurement={active:true,a:state.measurement.a,b:point};
    render();
});
// Direct dragging is snapped to 0.25 m and only creates a preview, never an implicit commit.
$('#plan-host').addEventListener('pointerdown', e => { if (e.button !== 0 || state.readOnly || state.preview || state.measurement.active)
    return; const group = e.target.closest('[data-room-id]'); if (!group)
    return; const r = model().levels.flatMap(l => l.rooms).find(r => r.id === group.dataset.roomId); if (!r || r.locked)
    return; const svg = group.ownerSVGElement, pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; const p = pt.matrixTransform(svg.getScreenCTM().inverse()); drag = { id: r.id, x: r.x, y: r.y, clientX: e.clientX, clientY: e.clientY, start: p, svg, group, moved: false }; });
document.addEventListener('pointermove', e => { if (!drag)
    return; if (Math.hypot(e.clientX - drag.clientX, e.clientY - drag.clientY) > 7) {
    drag.moved = true;
    drag.group.style.opacity = '.65';
} });
document.addEventListener('pointerup', e => { if (!drag)
    return; const d = drag; drag = null; d.group.style.opacity = ''; if (!d.moved)
    return; ignoreClickUntil = Date.now() + 500; const pt = d.svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; const p = pt.matrixTransform(d.svg.getScreenCTM().inverse()), dx = Math.round((p.x - d.start.x) * 4) / 4, dy = -Math.round((p.y - d.start.y) * 4) / 4; state.selectedId = d.id; try {
    stage({ type: 'move', roomId: d.id, x: round(d.x + dx), y: round(d.y + dy) }, 'نقل مساحة بالسحب');
}
catch (err) {
    reportError(err);
} });
document.addEventListener('pointercancel', () => { if (drag)
    drag.group.style.opacity = ''; drag = null; });
async function boot() {
    icons();
    await api.init();
    let loaded = false;
    const shareToken = new URLSearchParams(location.search).get('share');
    if (shareToken) {
        try {
            if (!api.available)
                throw Error('فتح رابط المراجعة يحتاج الخادم المتصل.');
            const data = await api.request('/api/shares/' + encodeURIComponent(shareToken));
            setProject(createHistory(assertModel(data.model)), { readOnly: true, shareToken });
            loaded = true;
        }
        catch (e) {
            // Fail closed: an invalid review link must never fall back to another private local project.
            $('#app').hidden=true;
            showModal('رابط المراجعة غير متاح',`<p class="notice error">${E(e.message)}</p><p>لم نفتح مشروعًا آخر بدل هذا الرابط.</p><div class="modal-footer"><a href="/" class="btn primary">فتح استوديو مسار</a></div>`);
            return;
        }
    }
    if (!loaded) {
        try {
            const projects = await listLocal();
            if (projects.length) {
                setProject(assertHistory(projects[0].history));
                for(const [k,v] of Object.entries(await loadLocalVersions(projects[0].id)))state.versions.set(k,v);
                saveStatus('استُعيد آخر مشروع محفوظ على هذا الجهاز');
                loaded = true;
            }
        }
        catch (e) {
            toast(e.message, true);
        }
    }
    if (!loaded) {
        const brief = understand('أرض 20×25 متر. فيلا ثلاثة أدوار إجمالًا، خمس غرف نوم، مجلس ضيوف ومعيشة عائلية، وحديقة خلفية. الشارع جنوب.');
        const m = generate(brief);
        m.requirements.push({ id: 'r-detail-review', label: 'الخصوصية وتفاصيل الطلب الأصلي تحتاج مراجعة معمارية؛ لم تُفحص آليًا.', type: 'custom', source: 'requested', locked: true });
        setProject(createHistory(m), { demo: true });
        saveStatus('مثال توضيحي · ابدأ مشروعًا جديدًا لحفظ فكرتك');
    }
    $('#system-status').textContent = api.available ? 'المحرك المحلي والخادم متصلان' : 'المحرك المحلي جاهز · بلا خادم';
    if(api.available&&api.persistenceClass==='ephemeral'){const banner=document.createElement('div');banner.id='persistence-warning';banner.className='storage-banner';banner.setAttribute('role','status');banner.textContent='بيئة معاينة: تخزين الحسابات والمشاريع على الخادم مؤقت وقد يُفقد عند إعادة التشغيل. احفظ نسخة JSON على جهازك؛ هذه ليست استضافة إنتاجية دائمة.';const bar=document.querySelector('.topbar');if(bar)bar.after(banner);else document.body.prepend(banner);}
}
boot().catch(e => { reportError(e); $('#system-status').textContent = 'تعذّر بدء المشروع. راجع الرسالة وأعد المحاولة.'; });
