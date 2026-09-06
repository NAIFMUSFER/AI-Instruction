"""Bounded local probes; no provider call and no request to a public server."""
import asyncio, base64, copy, io, json, sys, time
from pathlib import Path
root, out = [Path(x).resolve() for x in sys.argv[1:3]]
sys.path.insert(0, str(root)); out.mkdir(parents=True, exist_ok=True)
import httpx
import acs_understand_api as A
import acs_upload_security as UP
from starlette.formparsers import MultiPartParser
from PIL import Image
base = {'site': {'w': 20, 'd': 25}, 'floor_height': 3.2, 'wall_h': 3,
        'levels': [{'index': 0, 'template': 'g'}],
        'floors': {'g': {'rooms': [{'id': 'room', 'rect': [0,0,6,6],
        'walls': 'full', 'doors': [{'edge':'N','offset':3,'width':1,'height':2.1}]}]}},
        'meta': {'strict': True}}
buf = io.BytesIO(); Image.new('RGB', (8,8)).save(buf, format='PNG'); png=buf.getvalue()
captured=[]; rows=[]; field_bytes=[0]
async def run_job(target, kwargs, *args, **kw):
    captured.append({'target':target, 'fields':{k:v for k,v in kwargs.items() if k!='images'}})
    return copy.deepcopy(base)
async def validate(name, *args):
    if name=='validate_images': return UP.validate_images(*args)
    raise AssertionError('unexpected validation operation '+name)
async def authority(b): return {'available': True, 'proposals':[]}, b
old_job,old_validate,old_authority = A.run_job,A._validate,A._engineering_authority
old_part = MultiPartParser.on_part_data
def part(self,data,start,end):
    if self._current_part.file is None: field_bytes[0]+=end-start
    return old_part(self,data,start,end)
async def main():
    A.run_job=run_job; A._validate=validate; A._engineering_authority=authority
    MultiPartParser.on_part_data=part
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=A.app),base_url='http://audit.local') as c:
        for name, data in [('image_nonfinite_site',{'site_w':'nan','site_d':'-20','floors':'-1'}),
            ('oversized_unused_form_field',{'unused':'X'*(A.MAX_UPLOAD+1024)})]:
            field_bytes[0]=0;captured.clear();t=time.perf_counter()
            res=await c.post('/v1/understand/image',data=data,files={'files':('audit.png',png,'image/png')})
            cap=copy.deepcopy(captured)
            # JSON evidence represents non-finite values as strings, never invalid JSON.
            for call in cap:
                for k,v in list(call['fields'].items()):
                    if isinstance(v,float) and not __import__('math').isfinite(v):call['fields'][k]=str(v)
            rows.append({'case':name,'status':res.status_code,'parsed_nonfile_bytes':field_bytes[0],
                'declared_upload_max':A.MAX_UPLOAD,'seconds':time.perf_counter()-t,
                'generation_calls':cap,'scope':'real ASGI/form parsing, real image validation; generation and proposal stage are doubles'})
    A.run_job,A._validate,A._engineering_authority=old_job,old_validate,old_authority
    MultiPartParser.on_part_data=old_part
asyncio.run(main())
gl=json.loads((out.parent/'model-probes/explicit-elevation.gltf').read_text())
floor=next(n for n in gl['nodes'] if n.get('name','').startswith('FLOOR|'))
acc=gl['accessors'][gl['meshes'][floor['mesh']]['primitives'][0]['attributes']['POSITION']]
rows.append({'case':'exported_floor_elevation','declared_top_y_m':7.5,
    'actual_gltf_y_min_m':acc['min'][1],'actual_gltf_y_max_m':acc['max'][1]})
(out/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
print(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False))
