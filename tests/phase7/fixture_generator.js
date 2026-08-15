/* يولّد تجهيزات المرحلة 7 من تجهيزات المستودع القائمة — لا نموذج مخترَع.
   النماذج المزجَّجة تضيف نوافذ على الحواف الخارجية فقط، كي تكون هناك فتحات
   واجهة حقيقية يمكن قياس انحرافها. */
const fs=require('fs'), path=require('path');
const HERE=__dirname, ROOT=path.resolve(HERE,'..','..');
const BASE=JSON.parse(fs.readFileSync(
  path.join(ROOT,'tests','phase3','fixtures','base_fixtures.json'),'utf8'));
const C=o=>JSON.parse(JSON.stringify(o));

/* الحافة خارجية إن لم يلمسها فراغ آخر على الجانب الآخر */
function glaze(model,perRoom){
  const m=C(model);
  Object.keys(m.floors||{}).forEach(tk=>{
    const rooms=(m.floors[tk]||{}).rooms||[];
    const occupied=(x,z)=>rooms.some(r=>{
      const [rx,rz,rw,rd]=r.rect;
      return x>rx-0.01&&x<rx+rw+0.01&&z>rz-0.01&&z<rz+rd+0.01; });
    rooms.forEach(r=>{
      const [rx,rz,rw,rd]=r.rect;
      const cand=[
        ['N',rx+rw/2,rz-0.3],['S',rx+rw/2,rz+rd+0.3],
        ['W',rx-0.3,rz+rd/2],['E',rx+rw+0.3,rz+rd/2]];
      const out=[];
      cand.forEach(c=>{ if(!occupied(c[1],c[2])) out.push(c[0]); });
      r.windows=(r.windows||[]).slice();
      out.slice(0,perRoom).forEach(edge=>{
        const span=(edge==='N'||edge==='S')?rw:rd;
        if(span<2.0) return;
        r.windows.push({edge:edge,offset:Math.round((span/2)*100)/100,
          width:1.4,height:1.4,sill:0.9}); });
    });
  });
  m.meta=Object.assign({},m.meta,{name:(m.meta&&m.meta.name||'model')+'_glazed'});
  return m;
}

const out={
  villa_glazed: glaze(BASE.villa,2),
  hotel_glazed: glaze(BASE.hotel,1),
  clinic_glazed: glaze(BASE.clinic,2),
  warehouse_glazed: glaze(BASE.warehouse,1)
};
/* فيلا بدور واحد: مرجع صريح لفحص انحراف عدد الأدوار */
const single=C(out.villa_glazed);
single.levels=[single.levels[0]];
single.meta.name='villa_glazed_single_level';
out.villa_single_level=single;

fs.writeFileSync(path.join(HERE,'fixtures','render_fixtures.json'),
  JSON.stringify(out,null,1),'utf8');
const n=k=>{let w=0;Object.values(out[k].floors||{}).forEach(f=>(f.rooms||[]).forEach(r=>w+=(r.windows||[]).length));return w;};
Object.keys(out).forEach(k=>console.log(' ',k,'windows',n(k),'levels',out[k].levels.length));
console.log('render fixtures written:',Object.keys(out).length,'models');
