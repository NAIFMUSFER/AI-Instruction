/** Small DOM lifecycle unit fixture; the separate browser test uses real Chromium. */
import test from 'node:test';
import assert from 'node:assert/strict';
import {openRenderStudio} from '../src/render-ui.js';
import {generate,understand} from '../shared/model.js';
function element(tagName='DIV') {
    const listeners=new Map();
    return {tagName,isConnected:true,open:true,disabled:true,value:'',checked:false,textContent:'',innerHTML:'',
        addEventListener(name,fn,options){const list=listeners.get(name)||[];list.push({fn,once:options?.once});listeners.set(name,list);},
        removeEventListener(name,fn){listeners.set(name,(listeners.get(name)||[]).filter(row=>row.fn!==fn));},
        async emit(name,event={}){for(const row of [...(listeners.get(name)||[])]){if(row.once)this.removeEventListener(name,row.fn);await row.fn({currentTarget:this,preventDefault(){},...event});}}
    };
}
async function fixture(run) {
    const previous=globalThis.document,host=element(),dialog=element(),nodes=new Map();
    const node=selector=>{if(!nodes.has(selector))nodes.set(selector,element(selector==='#render-start'?'BUTTON':'DIV'));return nodes.get(selector);};
    host.querySelector=node;globalThis.document={getElementById:id=>id==='modal'?dialog:host};
    let resolveCapability,requests=[];const model=generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم'));
    const api={available:true,user:{id:'unit-owner'},request:route=>{requests.push(route);return route.endsWith('/capabilities')?new Promise(resolve=>{resolveCapability=resolve;}):Promise.resolve({jobs:[]});}};
    try {
        const opened=openRenderStudio({api,getModel:()=>model,getRevision:()=> 'unit-revision',getCloudVersion:()=>1,isPending:()=>false,isReadOnly:()=>false,saveCloud:async()=>{},showModal(){},onSelect(){},reportError(error){throw error;}});
        await run({dialog,node,requests,opened,resolveCapability:value=>resolveCapability(value)});
    } finally {
        dialog.open=false;await dialog.emit('close');host.isConnected=false;
        if(previous===undefined)delete globalThis.document;else globalThis.document=previous;
    }
}
test('a delayed close event from a previous dialog does not dispose the newly opened render panel',async()=>{
    await fixture(async({dialog,node,requests,opened,resolveCapability})=>{
        await dialog.emit('close'); // Delivery after the shared dialog was already reopened.
        resolveCapability({enabled:true,workerOnline:true,retentionDays:7,storage:'local'});await opened;
        assert.equal(node('#render-start').disabled,false);
        assert.match(node('#render-capability').textContent,/متصل/);
        assert.deepEqual(requests,['/api/renders/capabilities','/api/renders']);
    });
});
test('delegated job handlers leave native artifact download anchors uncancelled',async()=>{
    await fixture(async({node,opened,resolveCapability})=>{
        resolveCapability({enabled:true,workerOnline:true,retentionDays:7,storage:'local'});await opened;
        let prevented=false;
        await node('#render-jobs').emit('click',{target:{closest:()=>null},preventDefault(){prevented=true;}});
        assert.equal(prevented,false,'The ordinary anchor download must retain its native default action');
    });
});
