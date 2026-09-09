/** Read-only room review. Areas are canonical polygon areas, never permit/clear areas.
 * Export contracts intentionally exclude the original brief, comments and account data.
 */
import { assertModel, area, round, clone, KINDS, normalizeText } from '../shared/model.js';
import { escapeHTML } from '../shared/geometry.js';
import { csvCell } from '../shared/building.js';
export const ROOM_SCHEDULE_SCHEMA = 'masar-room-schedule-1';
const disclaimer = 'مساحات مضلعات النموذج المفاهيمي وليست مساحات صافية بعد التشطيب أو مسطحات رخصة. مجموع الأدوار ليس بصمة الأرض. عدد الفتحات لا يثبت التهوية أو الإضاءة أو السلامة. التقرير للقراءة وليس ملف مشروع قابلًا للاستيراد.';
export function roomSchedule(model, revisionLabel = '') {
    const m = assertModel(model);
    if (typeof revisionLabel !== 'string' || revisionLabel.length > 1000) throw Error('مرجع نسخة التقرير غير صالح.');
    const levels = m.levels.map(level => {
        const rooms = level.rooms.map(room => ({
            id: room.id, name: room.name, kind: room.kind, kindLabel: KINDS[room.kind] || room.kind,
            levelId: level.id, levelName: level.name,
            shape: room.footprint ? 'polygon' : 'rectangle', polygonAreaM2: area(room),
            bounds: { x: room.x, y: room.y, width: room.w, depth: room.d }, heightM: room.height,
            doors: (room.doors || []).map(d => ({ id:d.id, side:d.side, widthM:d.width, heightM:d.height ?? 2.15, heightSource:d.height === undefined ? 'concept-default' : 'model', entry:!!d.entry })),
            windows: (room.windows || []).map(w => ({ id:w.id, side:w.side, widthM:w.width, heightM:w.height ?? null, sillM:w.sill ?? null })),
            locked: !!room.locked
        }));
        return { id: level.id, name: level.name, elevationM: level.elevation, spaceCount: rooms.length,
            polygonAreaSumM2: round(rooms.reduce((sum,r) => sum+r.polygonAreaM2,0)), rooms };
    });
    return { schema: ROOM_SCHEDULE_SCHEMA, units: 'm', areaUnits: 'm2',
        source: { modelId:m.id, title:m.title, revisionLabel, siteWidthM:m.site.width, siteDepthM:m.site.depth },
        spaceCount: levels.reduce((sum,l)=>sum+l.spaceCount,0), levels, disclaimer };
}
export function roomScheduleCSV(model, revisionLabel = '') {
    const data = roomSchedule(model, revisionLabel);
    const header = ['المشروع','معرف المشروع','مرجع النسخة','الدور','معرف المساحة','اسم المساحة','النوع','الشكل','مساحة المضلع المفاهيمي م2','عرض الصندوق المحيط م','عمق الصندوق المحيط م','ارتفاع الغرفة م','عناصر الأبواب بالغرفة','عناصر النوافذ بالغرفة','مثبتة','حدود التقرير'];
    const rows = data.levels.flatMap(level=>level.rooms.map(r=>[
        data.source.title,data.source.modelId,data.source.revisionLabel,level.name,r.id,r.name,r.kindLabel,
        r.shape==='polygon'?'مضلع؛ الصندوق المحيط ليس مساحة قابلة للتأثيث':'مستطيل',r.polygonAreaM2,r.bounds.width,r.bounds.depth,r.heightM,
        r.doors.length,r.windows.length,r.locked?'نعم':'لا',disclaimer
    ]));
    return '\uFEFF'+[header,...rows].map(row=>row.map(csvCell).join(',')).join('\r\n');
}
export function filterRoomRows(schedule, levelId, query = '') {
    const level = schedule.levels.find(l=>l.id===levelId);
    if (!level) return [];
    const q=normalizeText(String(query));
    return level.rooms.filter(r=>!q||normalizeText(r.name+' '+r.kindLabel+' '+r.id).includes(q));
}
export function attachRoomReview({ root, model, levelId, revisionLabel, showLevel, focusRoom, download }) {
    const snapshot=clone(assertModel(model)), data=roomSchedule(snapshot,revisionLabel), E=escapeHTML;
    let active=data.levels.find(l=>l.id===levelId)||data.levels[0], selected=null;
    const n=value=>Number(value).toLocaleString('en-US',{maximumFractionDigits:2});
    root.innerHTML=`<h3>الغرف والمساحات</h3><p>ابحث بالاسم ثم اضغط المساحة لتكبير موضعها. هذه القائمة للقراءة فقط وتشمل الخدمات والممرات.</p>
    <div class="room-review-fields"><label class="field"><span>الدور المعروض</span><select id="room-review-level">${data.levels.map(l=>`<option value="${E(l.id)}" ${l.id===active.id?'selected':''}>${E(l.name)}</option>`).join('')}</select></label><label class="field"><span>بحث عن غرفة أو نوع مساحة</span><input id="room-review-search" type="search" maxlength="120" autocomplete="off" placeholder="مثل: مطبخ، نوم، حمام"></label></div>
    <p id="room-review-summary"></p><output id="room-review-count" aria-live="polite"></output>
    <div id="room-review-list" class="room-review-list"></div><section id="room-review-detail" class="notice" aria-label="تفاصيل المساحة المحددة" hidden></section>
    <div class="notice warn">${E(disclaimer)}<br>أبعاد الصندوق المحيط في الغرفة غير المستطيلة ليست عرضًا صافيًا أو مساحة صالحة للأثاث.</div>
    <div class="room-review-downloads"><button class="btn light" type="button" data-room-report="csv">تنزيل جدول جميع الأدوار CSV</button><button class="btn light" type="button" data-room-report="json">تنزيل تقرير المساحات JSON</button></div>`;
    const select=root.querySelector('#room-review-level'), search=root.querySelector('#room-review-search'), list=root.querySelector('#room-review-list'), detail=root.querySelector('#room-review-detail');
    const side={north:'شمال',south:'جنوب',east:'شرق',west:'غرب'};
    function refresh() {
        const rows=filterRoomRows(data,active.id,search.value);
        root.dataset.levelId=active.id;
        root.querySelector('#room-review-summary').textContent=`${active.name}: ${active.spaceCount} مساحة ممثلة · مجموع المضلعات ${n(active.polygonAreaSumM2)} م² · كامل المشروع ${data.spaceCount} مساحة في ${data.levels.length} أدوار.`;
        root.querySelector('#room-review-count').textContent=`نتائج البحث: ${rows.length} من ${active.spaceCount}`;
        list.innerHTML=rows.length?rows.map(r=>`<button class="room-review-row" type="button" data-room-review-index="${active.rooms.indexOf(r)}" aria-pressed="${selected?.id===r.id}"><strong>${E(r.name)}</strong><span>${E(r.kindLabel)} · <b dir="ltr">${n(r.polygonAreaM2)} m²</b>${r.shape==='polygon'?' · غير مستطيلة':''}${r.locked?' · مثبتة':''}</span></button>`).join(''):'<p class="notice">لا توجد مساحة مطابقة في هذا الدور. غيّر البحث أو اختر دورًا آخر؛ لم يُحذف شيء من المشروع.</p>';
    }
    function resetSelection() { selected=null;detail.hidden=true;detail.textContent='';delete root.dataset.selectedRoomId; }
    select.addEventListener('change',()=>{
        const next=data.levels.find(l=>l.id===select.value);if(!next)return;
        active=next;resetSelection();showLevel(active.id);refresh();
    });
    search.addEventListener('input',refresh);
    list.addEventListener('click',event=>{
        const button=event.target.closest('[data-room-review-index]');if(!button||!list.contains(button))return;
        const room=active.rooms[Number(button.dataset.roomReviewIndex)];if(!room)return;
        selected=room;root.dataset.selectedRoomId=room.id;
        focusRoom(room.id,active.id);
        const doors=room.doors.map(d=>`${side[d.side]||d.side}: ${n(d.widthM)} م${d.entry?' · معلّم كمدخل':''}`).join('، ');
        const windows=room.windows.map(w=>`${side[w.side]||w.side}: ${n(w.widthM)} م`).join('، ');
        detail.hidden=false;
        detail.innerHTML=`<h4>${E(room.name)}</h4><p>${E(active.name)} · ${E(room.kindLabel)}${room.locked?' · مثبتة في النموذج':''}</p><p>مساحة المضلع المفاهيمي: <b dir="ltr">${n(room.polygonAreaM2)} m²</b><br>${room.shape==='polygon'?'صندوق محيط فقط؛ الغرفة غير مستطيلة':'أبعاد مستطيل النموذج'}: <b dir="ltr">${n(room.bounds.width)} × ${n(room.bounds.depth)} m</b><br>ارتفاع النموذج: <b dir="ltr">${n(room.heightM)} m</b></p><p>عناصر الأبواب: ${room.doors.length}${doors?' — '+E(doors):''}<br>عناصر النوافذ: ${room.windows.length}${windows?' — '+E(windows):''}</p><small>عرض الفتحة من النموذج؛ لا يثبت عرض المرور الصافي أو كفاية الإضاءة. لم يتغير التوزيع أو السجل.</small>`;
        list.querySelectorAll('[data-room-review-index]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.roomReviewIndex)===active.rooms.indexOf(room))));
    });
    root.querySelector('[data-room-report="csv"]').addEventListener('click',()=>download('MASAR-Room-Schedule.csv',roomScheduleCSV(snapshot,revisionLabel),'text/csv;charset=utf-8'));
    root.querySelector('[data-room-report="json"]').addEventListener('click',()=>download('MASAR-Room-Schedule.json',JSON.stringify(data,null,2),'application/json'));
    refresh();
}
