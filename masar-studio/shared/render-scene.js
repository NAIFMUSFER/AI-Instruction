/** Immutable render contract. Metres, +X east, +Y north, +Z up.
 * Geometry comes only from MASAR; finishes/furniture are presentation assumptions.
 * No prompt, account, comments, reference uploads, paths, URLs or executable input.
 */
import { assertModel, validate, roomPolygon, pointInPolygon, area } from './model.js';
import { deriveBuildingGraph } from './building.js';
export const RENDER_SCHEMA = 'masar-render-scene-1';
export const RENDER_PIPELINE = 'blender-bridge-1.0.0';
export const RENDER_QUALITIES = Object.freeze({ preview: { width: 640, height: 480, samples: 16 }, standard: { width: 1280, height: 960, samples: 64 } });
export const RENDER_FINISHES = Object.freeze({
    warm: { label: 'حجر فاتح وخشب دافئ', wall: '#ddd6c6', floor: '#b48c63', frame: '#343d3b', interior: '#f0ebe1' },
    white: { label: 'أبيض مع أرضية فاتحة', wall: '#ebe9e3', floor: '#d2c6b6', frame: '#353d45', interior: '#f4f1e9' },
    slate: { label: 'حجر رمادي وخشب', wall: '#929b9b', floor: '#a68159', frame: '#272e34', interior: '#e4e2dc' }
});
const number = n => Math.round(n * 1e6) / 1e6;
export function stableJSON(value) {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return '[' + value.map(stableJSON).join(',') + ']';
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stableJSON(value[k])).join(',') + '}';
}
export function renderSettings(input = {}) {
    if (!input || typeof input !== 'object' || Array.isArray(input)) throw Error('إعدادات الإخراج غير صالحة.');
    for (const key of Object.keys(input)) if (!['quality', 'finish', 'roomId', 'furniture'].includes(key)) throw Error('إعداد إخراج غير مدعوم: ' + key);
    const { quality = 'preview', finish = 'warm', roomId = null, furniture = true } = input;
    if (!Object.hasOwn(RENDER_QUALITIES, quality) || !Object.hasOwn(RENDER_FINISHES, finish)) throw Error('اختر جودة وتشطيبًا من القائمة.');
    if ((roomId !== null && (typeof roomId !== 'string' || roomId.length > 160)) || typeof furniture !== 'boolean') throw Error('إعدادات الغرفة أو الأثاث غير صالحة.');
    return { quality, finish, roomId, furniture };
}
function cells(room) {
    const poly = roomPolygon(room), xs = [...new Set(poly.map(p => p[0]))].sort((a,b)=>a-b), ys = [...new Set(poly.map(p=>p[1]))].sort((a,b)=>a-b), out=[];
    for (let i=1;i<xs.length;i++) for(let j=1;j<ys.length;j++) {
        const x=xs[i-1], y=ys[j-1], w=xs[i]-x, d=ys[j]-y;
        if (w>0 && d>0 && pointInPolygon([x+w/2,y+d/2],poly,false)) out.push({ x,y,w,d });
    }
    return out;
}
export function createRenderScene(model, revisionId, input = {}) {
    assertModel(model);
    if (typeof revisionId !== 'string' || !revisionId || revisionId.length > 160) throw Error('رقم نسخة المشروع مطلوب.');
    const blockers = validate(model).filter(i => i.status === 'error');
    if (blockers.length) throw Error('عالج تعارضات النموذج قبل الإخراج: ' + blockers.map(i=>i.message || i.title || i.id).slice(0,3).join('، '));
    const settings = renderSettings(input), finish=RENDER_FINISHES[settings.finish], graph=deriveBuildingGraph(model);
    if (graph.elements.openings.some(o=>!o.hostWallId)) throw Error('توجد فتحة بلا جدار مضيف صالح.');
    const materials = {
        exterior: { color:finish.wall, roughness:.7, metallic:0 }, interior: {color:finish.interior,roughness:.8,metallic:0},
        floor: {color:finish.floor,roughness:.42,metallic:0,clearcoat:.08}, frame: {color:finish.frame,roughness:.26,metallic:.72},
        glass: {color:'#c4e2e6',roughness:.07,metallic:0,alpha:.38,transmission:.58,ior:1.45,clearcoat:.35,thickness:.015},
        wood: {color:'#98724d',roughness:.4,metallic:0,clearcoat:.12}, fabric: {color:'#e2d7c7',roughness:.95,metallic:0},
        site: {color:'#7f966d',roughness:1,metallic:0}, paving: {color:'#c6c2b7',roughness:.82,metallic:0},
        coping: {color:'#d9d4c9',roughness:.72,metallic:0}, water:{color:'#4b9bad',roughness:.08,metallic:0,alpha:.88,transmission:.12,ior:1.333,clearcoat:1,clearcoatRoughness:.06,thickness:.08}
    };
    const objects=[], proofs={ rooms:[], walls:[], openings:[] };
    function box(id, xyz, whd, mat, meta={}) {
        if (![...xyz,...whd].every(Number.isFinite) || whd.some(n=>n<=0)) throw Error('هندسة إخراج غير صالحة.');
        objects.push({ id, shape:'box', min:xyz.map(number), size:whd.map(number), material:mat, ...meta });
    }
    for(const level of model.levels) {
        for(const room of level.rooms) {
            const floor=cells(room);
            proofs.rooms.push({id:room.id,levelId:level.id,area:area(room),polygon:roomPolygon(room),height:room.height,elevation:level.elevation});
            floor.forEach((c,i)=>box(`floor:${room.id}:${i}`,[c.x,c.y,level.elevation-.16],[c.w,c.d,.16],'paving',{elementId:room.id,roomId:room.id,levelId:level.id,category:'space-floor',displayOnly:false}));
            // A separate 10 mm presentation finish prevents coincident faces with
            // lower-level wall caps without shortening canonical floor-to-floor walls.
            floor.forEach((c,i)=>box(`finish:${room.id}:${i}`,[c.x,c.y,level.elevation],[c.w,c.d,.01],'floor',{elementId:`finish:${room.id}`,roomId:room.id,levelId:level.id,category:'floor-finish',displayOnly:true}));
            // Preserve explicitly lower room ceiling heights; thickness is presentation-only.
            if(room.height<level.height-1e-6) floor.forEach((c,i)=>box(`ceiling:${room.id}:${i}`,[c.x,c.y,level.elevation+room.height],[c.w,c.d,.03],'interior',{elementId:`ceiling:${room.id}`,roomId:room.id,levelId:level.id,category:'ceiling',displayOnly:true}));
            // Only decorative furniture; never a structural or circulation claim.
            const c=floor.slice().sort((a,b)=>b.w*b.d-a.w*a.d)[0];
            if(settings.furniture && c && c.w>=3 && c.d>=3) {
                const meta={elementId:`decor:${room.id}`,roomId:room.id,levelId:level.id,category:'furniture',displayOnly:true};
                if(['living','majlis','bedroom'].includes(room.kind)) {
                    box(`furn:${room.id}:base`,[c.x+.35,c.y+.35,level.elevation+.14],[Math.min(2.5,c.w-.7),room.kind==='bedroom'?2:.85,.38],'fabric',meta);
                    box(`furn:${room.id}:back`,[c.x+.35,c.y+.35,level.elevation+.52],[Math.min(2.5,c.w-.7),.13,.4],'wood',meta);
                    if(room.kind==='bedroom'){for(let i=0;i<2;i++)box(`furn:${room.id}:pillow:${i}`,[c.x+.55+i*.9,c.y+.55,level.elevation+.52],[.7,.42,.12],'fabric',meta);}
                    else {for(let i=0;i<2;i++)box(`furn:${room.id}:arm:${i}`,[c.x+.35+i*(Math.min(2.5,c.w-.7)-.13),c.y+.35,level.elevation+.52],[.13,.85,.2],'fabric',meta);}
                    if(room.kind!=='bedroom') box(`furn:${room.id}:table`,[c.x+.8,c.y+1.65,level.elevation+.07],[1.3,.68,.37],'wood',meta);
                } else if(['dining','kitchen','office'].includes(room.kind)) {
                    box(`furn:${room.id}:top`,[c.x+c.w*.3,c.y+c.d*.35,level.elevation+.72],[c.w*.4,Math.min(1.1,c.d*.3),.08],'wood',meta);
                    for(let i=0;i<2;i++) box(`furn:${room.id}:support:${i}`,[c.x+c.w*(.33+i*.3),c.y+c.d*.4,level.elevation],[.08,.65,.72],'frame',meta);
                }
            }
        }
        // Full-height wall cells subtract the UNION of all hosted apertures, also
        // supporting vertically separated apertures. No display-height truncation.
        for(const wall of graph.elements.walls.filter(w=>w.levelId===level.id)) {
            const opens=graph.elements.openings.filter(o=>o.hostWallId===wall.id);
            const cuts=opens.map(o=>{const a=wall.axis==='h'?o.x:o.y;return {a:a-o.width/2,b:a+o.width/2,z:o.sill,top:o.sill+o.height};});
            const along=[...new Set([wall.start,wall.end,...cuts.flatMap(c=>[c.a,c.b])])].sort((a,b)=>a-b);
            const heights=[...new Set([0,wall.height,...cuts.flatMap(c=>[c.z,c.top])])].sort((a,b)=>a-b);
            const before=objects.length;
            for(let i=1;i<along.length;i++) for(let j=1;j<heights.length;j++) {
                const a=along[i-1],b=along[i],z=heights[j-1],top=heights[j], mid=(a+b)/2,mz=(z+top)/2;
                if(b-a<1e-6||top-z<1e-6||a<wall.start-1e-5||b>wall.end+1e-5||z<0||top>wall.height+1e-5) continue;
                if(cuts.some(c=>mid>c.a-1e-7&&mid<c.b+1e-7&&mz>c.z-1e-7&&mz<c.top+1e-7)) continue;
                const v=wall.axis==='v';
                box(`${wall.id}:cell:${i}:${j}`,[v?wall.coord-wall.thickness/2:a,v?a:wall.coord-wall.thickness/2,level.elevation+z],[v?wall.thickness:b-a,v?b-a:wall.thickness,top-z],wall.external?'exterior':'interior',{elementId:wall.id,roomIds:wall.adjacentRoomIds,levelId:level.id,category:'wall',displayOnly:false});
            }
            proofs.walls.push({id:wall.id,height:wall.height,thickness:wall.thickness,axis:wall.axis,coord:wall.coord,start:wall.start,end:wall.end,elevation:level.elevation,objectIds:objects.slice(before).map(o=>o.id),apertures:cuts});
        }
    }
    for(const o of graph.elements.openings) {
        const wall=graph.elements.walls.find(w=>w.id===o.hostWallId),v=wall.axis==='v',s=.055,depth=Math.min(wall.thickness,.12),bottom=o.z+o.sill;
        const meta={elementId:o.id,roomId:o.roomId,levelId:o.levelId,hostWallId:wall.id,category:o.type,displayOnly:true};
        const openingBox=(suffix,start,z,width,h,mat,d=depth)=>box(`${o.id}:${suffix}`,[v?o.x-d/2:o.x-o.width/2+start,v?o.y-o.width/2+start:o.y-d/2,z],[v?d:width,v?width:d,h],mat,meta);
        openingBox('left',0,bottom,s,o.height,'frame');openingBox('right',o.width-s,bottom,s,o.height,'frame');openingBox('head',s,bottom+o.height-s,o.width-2*s,s,'frame');
        if(o.type==='window') {
            openingBox('sill',s,bottom,o.width-2*s,s,'frame');
            openingBox('glass',s,bottom+s,o.width-2*s,o.height-2*s,'glass',.02);
        } else openingBox('leaf',s,bottom,o.width-2*s,o.height-s,'wood',.035);
        proofs.openings.push({id:o.id,hostWallId:o.hostWallId,x:o.x,y:o.y,z:bottom,width:o.width,height:o.height});
    }
    const top=model.levels.at(-1);
    // Polygon-aware roof plates, not a rectangular cover across an L-shaped void.
    for(const r of top.rooms) cells(r).forEach((c,i)=>box(`roof:${r.id}:${i}`,[c.x,c.y,top.elevation+top.height],[c.w,c.d,.16],'exterior',{elementId:`roof:${top.id}`,levelId:top.id,category:'roof',displayOnly:true}));
    box('presentation:site',[0,0,-.32],[model.site.width,model.site.depth,.15],'site',{elementId:'presentation:site',category:'site',displayOnly:true});
    for(const f of graph.elements.siteFeatures) {
        const meta={elementId:f.id,category:'site-feature',displayOnly:true};
        if(f.type==='pool') {
            const edge=Math.min(.18,f.w*.12,f.d*.12);
            box(`presentation:${f.id}:water`,[f.x+edge,f.y+edge,-.152],[Math.max(.05,f.w-edge*2),Math.max(.05,f.d-edge*2),.028],'water',{...meta,category:'pool-water'});
            box(`presentation:${f.id}:coping:n`,[f.x,f.y+f.d-edge,-.153],[f.w,edge,.03],'coping',{...meta,category:'pool-coping'});
            box(`presentation:${f.id}:coping:s`,[f.x,f.y,-.153],[f.w,edge,.03],'coping',{...meta,category:'pool-coping'});
            if(f.d>edge*2){
                box(`presentation:${f.id}:coping:e`,[f.x+f.w-edge,f.y+edge,-.153],[edge,f.d-edge*2,.03],'coping',{...meta,category:'pool-coping'});
                box(`presentation:${f.id}:coping:w`,[f.x,f.y+edge,-.153],[edge,f.d-edge*2,.03],'coping',{...meta,category:'pool-coping'});
            }
        } else box(`presentation:${f.id}`,[f.x,f.y,-.155],[f.w,f.d,.035],'paving',meta);
    }
    if(objects.length>16000) throw Error('المشهد يتجاوز حد عناصر الإخراج لهذه النسخة.');
    const allRooms=model.levels.flatMap(l=>l.rooms.map(r=>({...r,elevation:l.elevation,levelId:l.id})));
    const interiorRoom=settings.roomId?allRooms.find(r=>r.id===settings.roomId):allRooms.filter(r=>['living','majlis','bedroom','office'].includes(r.kind)).sort((a,b)=>['living','majlis','bedroom','office'].indexOf(a.kind)-['living','majlis','bedroom','office'].indexOf(b.kind)||a.elevation-b.elevation||area(b)-area(a))[0]||allRooms[0];
    if(!interiorRoom) throw Error('غرفة التصوير غير موجودة في النسخة.');
    const cell=cells(interiorRoom).sort((a,b)=>b.w*b.d-a.w*a.d)[0];
    const h=top.elevation+top.height, W=model.site.width,D=model.site.depth;
    return {
        schema:RENDER_SCHEMA,pipeline:RENDER_PIPELINE,units:'m',axes:'X-east Y-north Z-up',
        source:{modelId:model.id,revisionId,sourceSchema:model.schemaVersion},settings,
        resolution:{...RENDER_QUALITIES[settings.quality]},materials,objects,proofs,
        presentationAssumptions:{floorPlateThicknessM:.16,floorFinishThicknessM:.01,roofPlateThicknessM:.16,ceilingLinerThicknessM:.03,framingAndFurniture:'schematic, not manufactured specifications'},
        cameras:{exterior:{position:[W*1.45,-D*.65,h+Math.max(W,D)*.5],target:[W/2,D/2,h*.4],lens:45},interior:{position:[cell.x+cell.w*.88,cell.y+cell.d*.86,interiorRoom.elevation+Math.min(1.55,interiorRoom.height*.55)],target:[cell.x+cell.w*.28,cell.y+cell.d*.25,interiorRoom.elevation+1.0],lens:20,roomId:interiorRoom.id}},
        disclaimer:'Concept visualization; not construction approval. Floor/roof thickness, materials, framing and furniture are presentation assumptions. No structural, MEP, fire or SBC verification.'
    };
}
