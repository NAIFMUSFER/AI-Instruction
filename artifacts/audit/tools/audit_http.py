import json, os, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

root=Path(sys.argv[1]).resolve(); out=Path(sys.argv[2]).resolve()
out.mkdir(parents=True,exist_ok=True)
cases=[{'name':'warehouse','request':{'text':'مستودع بسيط 20×15 م من دور واحد، مساحة تخزين مفتوحة بباب واحد، بدون فرز وبدون مكاتب.','site_w':20,'site_d':15,'floors':1,'strict':True,'btype':'warehouse'}},
       {'name':'chalet','request':{'text':'شاليه 3 أدوار على أرض 20×25 م. في الأرضي صالة 6×5 م ومطبخ 4×4 م ودرج 3×4 م، وفي كل من الدورين العلويين غرفتا نوم 4×4 م وحمام 2×3 م، والدرج في الموضع نفسه بين الأدوار.','site_w':20,'site_d':25,'floors':3,'strict':True,'btype':'residential'}}]
(out/'requests.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
def request(base,path,name,data=None,headers=None,method=None,timeout=15):
    start=time.monotonic(); req=urllib.request.Request(base+path,
      data=json.dumps(data,ensure_ascii=False).encode() if data else None,
      headers={'Content-Type':'application/json',**(headers or {})},method=method)
    rec={'url':base+path,'method':req.get_method(),'request':data}
    try:
        try: resp=urllib.request.urlopen(req,timeout=timeout)
        except urllib.error.HTTPError as err: resp=err
        body=resp.read().decode(errors='replace')
        rec.update(status=resp.code,headers={k:v for k,v in resp.headers.items() if k.lower() in ('content-type','access-control-allow-origin','access-control-allow-headers','access-control-expose-headers','content-security-policy','x-request-id','retry-after')})
        try: rec['body']=json.loads(body)
        except ValueError: rec['body_text']=body[:4000]
    except Exception as err: rec['connection_error']=type(err).__name__+': '+str(err)
    rec['seconds']=round(time.monotonic()-start,3)
    (out/(name+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
    print(name,rec.get('status'),rec.get('connection_error',''),rec['seconds'],flush=True)
    return rec

if '--live' in sys.argv:
    base='https://acs-engine.onrender.com'
    health=request(base,'/health','live-health',timeout=20)
    request(base,'/ready','live-ready',timeout=20)
    request(base,'/version','live-version',timeout=20)
    for origin,name in [('https://sprightly-selkie-d906c3.netlify.app','allowed'),('https://audit-untrusted.example','disallowed')]:
        request(base,'/v1/understand','live-cors-'+name,method='OPTIONS',headers={'Origin':origin,'Access-Control-Request-Method':'POST'},timeout=20)
    request('https://sprightly-selkie-d906c3.netlify.app','/','live-frontend',timeout=20)
    if health.get('status')==200 and '--generate' in sys.argv:
        for c in cases: request(base,'/v1/understand','live-'+c['name'],c['request'],timeout=190)
else:
    env=dict(os.environ,ACS_ENV='development',ACS_ALLOWED_ORIGINS='http://127.0.0.1:8080')
    log=(out/'api-startup.log').open('w')
    proc=subprocess.Popen([sys.executable,'-m','uvicorn','acs_understand_api:app','--host','127.0.0.1','--port','8001'],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
    try:
        for i in range(80):
            try:
                urllib.request.urlopen('http://127.0.0.1:8001/health',timeout=.2); break
            except Exception: time.sleep(.1)
        base='http://127.0.0.1:8001'
        for path in ('/health','/ready','/version','/openapi.json'): request(base,path,'local-'+path[1:].replace('.json',''))
        for c in cases: request(base,'/v1/understand','local-'+c['name'],c['request'])
        request(base,'/v1/understand','local-cors',method='OPTIONS',headers={'Origin':'http://127.0.0.1:8080','Access-Control-Request-Method':'POST'})
    finally:
        proc.terminate();proc.wait(timeout=15);log.close()
