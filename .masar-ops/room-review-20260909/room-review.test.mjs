import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {generate,understand,clone,roomPolygon,round} from '../shared/model.js';
import {roomSchedule,roomScheduleCSV,filterRoomRows} from '../src/room-review.js';
const prompt=await readFile(new URL('./fixtures/customer-chalet-ar.txt',import.meta.url),'utf8');
const make=()=>generate(understand(prompt));
function polygonArea(room){const p=roomPolygon(room);return round(Math.abs(p.reduce((sum,a,i)=>{const b=p[(i+1)%p.length];return sum+a[0]*b[1]-b[0]*a[1];},0))/2);}
function csvRows(text){
    const rows=[];let row=[],cell='',quoted=false;
    for(let i=0;i<text.length;i++){
        const ch=text[i];if(i===0&&ch==='\uFEFF')continue;
        if(ch==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}
        else if(ch===','&&!quoted){row.push(cell);cell='';}
        else if(ch==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}
        else cell+=ch;
    }
    row.push(cell);rows.push(row);assert.equal(quoted,false);return rows;
}
test('room report includes all 17 spaces including circulation and detached pool WC',()=>{
    const m=make(),s=roomSchedule(m,'revision-exact');assert.equal(s.schema,'masar-room-schedule-1');
    assert.equal(s.spaceCount,17);assert.equal(s.source.modelId,m.id);assert.equal(s.source.revisionLabel,'revision-exact');
    assert.deepEqual(s.levels[0].rooms.map(r=>r.id),m.levels[0].rooms.map(r=>r.id));
    assert.ok(s.levels[0].rooms.some(r=>r.id==='l0-pool-bath'));assert.ok(s.levels[0].rooms.some(r=>r.kind==='hall'));
});
test('every reported area is independently calculated from the canonical polygon, not its bounding box',()=>{
    const m=make(),s=roomSchedule(m),rows=s.levels[0].rooms;
    for(const [i,r] of rows.entries())assert.equal(r.polygonAreaM2,polygonArea(m.levels[0].rooms[i]),r.id);
    const master=rows.find(r=>r.id==='l0-master');assert.equal(master.shape,'polygon');
    assert.ok(master.polygonAreaM2<master.bounds.width*master.bounds.depth);
    assert.match(s.disclaimer,/ليست مساحات صافية/);
});
test('each floor and all circulation/service spaces are retained in multi-floor reports',()=>{
    const m=generate(understand('فيلا على أرض 20×25 ثلاثة أدوار خمس غرف نوم'));
    const s=roomSchedule(m);assert.equal(s.levels.length,3);
    assert.equal(s.spaceCount,m.levels.reduce((n,l)=>n+l.rooms.length,0));
    for(const [i,l] of s.levels.entries()){
        assert.equal(l.elevationM,m.levels[i].elevation);assert.equal(l.spaceCount,m.levels[i].rooms.length);
        assert.equal(l.polygonAreaSumM2,round(m.levels[i].rooms.reduce((sum,r)=>sum+polygonArea(r),0)));
    }
});
test('report creation and mutation of returned arrays cannot mutate source or history fields',()=>{
    const m=make(),before=clone(m),s=roomSchedule(m,'r1');
    s.levels[0].rooms[0].bounds.width=999;s.levels[0].rooms[0].doors[0].widthM=99;
    assert.deepEqual(m,before);roomScheduleCSV(m,'r2');assert.deepEqual(m,before);
});
test('reports do not duplicate private original brief comments or reference uploads',()=>{
    const m=make();m.brief.prompt='PRIVATE_ORIGINAL_TEXT_DO_NOT_EXPORT';
    const s=JSON.stringify(roomSchedule(m));assert.ok(!s.includes(m.brief.prompt));
    assert.ok(!Object.hasOwn(roomSchedule(m),'comments'));assert.ok(!Object.hasOwn(roomSchedule(m),'references'));
    assert.ok(!roomScheduleCSV(m).includes(m.brief.prompt));
});
test('Arabic search handles diacritics and spelling normalization without interpreting regex',()=>{
    const s=roomSchedule(make()),id=s.levels[0].id;
    assert.ok(filterRoomRows(s,id,'مَطْبَخ').some(r=>r.kind==='kitchen'));
    assert.equal(filterRoomRows(s,id,'نوم').filter(r=>r.kind==='bedroom').length,3);
    assert.equal(filterRoomRows(s,id,'[').length,0);assert.equal(filterRoomRows(s,'missing','').length,0);
    assert.equal(filterRoomRows(s,id,'').length,17);
});
test('CSV is BOM UTF-8 and includes every floor independently of UI filters',()=>{
    const m=generate(understand('فيلا 20×25 ثلاثة أدوار خمس غرف نوم'));
    const text=roomScheduleCSV(m,'revision-csv');assert.ok(text.startsWith('\uFEFF'));
    const rows=csvRows(text),s=roomSchedule(m);
    assert.equal(rows.length,s.spaceCount+1);assert.ok(rows.every(r=>r.length===16));
    assert.deepEqual(new Set(rows.slice(1).map(r=>r[3])),new Set(m.levels.map(l=>l.name)));
    assert.ok(rows.slice(1).every(r=>r[1]===m.id&&r[2]==='revision-csv'));
});
test('CSV preserves quotes commas and newlines while neutralizing spreadsheet formulas',()=>{
    const m=make();m.title='=HYPERLINK("unsafe")';m.levels[0].name='@floor';m.levels[0].rooms[0].name='غرفة, "نوم"\nسطر';
    const rows=csvRows(roomScheduleCSV(m,'+revision'));assert.equal(rows[1][0],"'"+m.title);
    assert.equal(rows[1][2],"'+revision");assert.equal(rows[1][3],"'@floor");assert.equal(rows[1][5],m.levels[0].rooms[0].name);
});
test('room opening summaries retain IDs sides widths and disclose an assumed door height',()=>{
    const m=make(),s=roomSchedule(m);for(const [i,r] of s.levels[0].rooms.entries()){
        const original=m.levels[0].rooms[i];assert.equal(r.doors.length,original.doors.length);assert.equal(r.windows.length,(original.windows||[]).length);
        for(const [j,d] of r.doors.entries()){assert.equal(d.id,original.doors[j].id);assert.equal(d.widthM,original.doors[j].width);assert.equal(d.heightSource,original.doors[j].height===undefined?'concept-default':'model');}
    }
});
test('invalid report sources and unbounded revision labels fail without fabricating a schedule',()=>{
    assert.throws(()=>roomSchedule({}));assert.throws(()=>roomSchedule(make(),'x'.repeat(1001)));
});
