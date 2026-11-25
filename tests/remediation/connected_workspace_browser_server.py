"""CI-only controlled authentication/provider; actual ACS workspace and storage.

This module is not packaged/deployed and binds loopback only. No live account,
provider key or production design is used.
"""
import argparse
import copy
import json
from pathlib import Path
import sqlite3
import sys
import time
import urllib.parse
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import acs_auth as AUTH
import acs_auth_gateway as G
import acs_plan_http as P
import acs_workspace_http as H
import acs_workspace_service as S
import acs_plan_sources as SOURCES
import acs_plan_session as SESSION
import acs_generation_job as JOBS
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from test_connected_workspace import PROJECT, ACTOR, model


def fixture_building(brief, requirements):
    kind='warehouse' if 'مستودع' in brief else 'residential'
    if kind!='residential' or not any(r.get('metric')=='unit_count' for r in requirements):
        return model(kind)
    quantities={r['metric']:r['expected'] for r in requirements if not r.get('role')}
    if any(quantities.get(key)!=number for key,number in (
            ('site_width_m',20),('site_depth_m',20),('level_count',1),('unit_count',2))):
        raise AssertionError('Unsupported synthetic residential fixture program')
    # A deterministic, explicitly synthetic two-apartment case. The fixture's
    # east-facing entrance makes B wider than 6 m, so the later width edit keeps
    # valid reciprocal openings and access. It is not evidence of live AI output.
    from acs_residential_layout import propose
    building=propose(brief+'\nجهة الشارع: شرق',requirements)
    if building is None:
        raise AssertionError('Synthetic two-unit fixture cannot satisfy this program')
    template=building['levels'][0]['template']
    rooms=building['floors'].pop(template)['rooms']
    a=next(room for room in rooms if not room.get('unit_id') and room['role']=='corridor')
    b=next(room for room in rooms if room.get('unit_id')=='apartment_1' and room['role']=='living')
    for room,identity in ((a,'a'),(b,'b')):
        room['id']=identity;room['name']=identity.upper();room['points'][0]['id']='light-'+identity
    building['floors']['ground']={'rooms':[a,b]+[room for room in rooms if room is not a and room is not b]}
    for level in building['levels']:level['template']='ground'
    building['meta'].update(type='residential',name='Synthetic two-apartment browser fixture',
                            acs_layout_method='ci_two_unit_geometry_fixture_v1')
    building['meta']['assumptions']=[
        'نموذج اصطناعي لاختبار برنامج شقتين؛ ليس ناتجًا عن استدعاء مزود حي.',
        'المدخل الشرقي اختيار ثابت لهذا الاختبار، وليس جهة شارع أكدها المستخدم.',
        *[item for item in building['meta']['assumptions'] if not item.startswith('توزيع بديل محسوب بعد تعذر')]]
    return building


class FixtureRunner:
    def __init__(self, counts, *, delay_seconds=1.2):
        self.counts, self.delay_seconds = counts, delay_seconds

    def run(self,target,kwargs,**controls):
        if target.endswith('generate_plan_candidate') or target=='acs_plan_sources:candidate':
            self.counts['generation']+=1;time.sleep(self.delay_seconds)
            return {'building':fixture_building(kwargs['brief'],kwargs['requirements']),'provider_calls':1}
        if target.endswith('budgeted_chat_candidate'):
            self.counts['chat']+=1
            candidate=copy.deepcopy(kwargs['building'])
            next(room for room in candidate['floors']['ground']['rooms'] if room['id']=='b')['rect'][2]=6
            return candidate
        if target.endswith('artifact_from_snapshot'):return S.artifact_from_snapshot(**kwargs)
        raise AssertionError(target)


def application(database):
    db=SQLitePlanStore(database)
    try:db.create_project(PROJECT,owner_id=ACTOR)
    except Exception:pass
    counts={'generation':0,'chat':0}
    projects=[{'id':PROJECT,'name':'مشروع التحقق','owner_id':ACTOR}]
    with sqlite3.connect(database) as con:
        con.execute('create table if not exists ci_jobs(id text primary key, document text)')
        con.execute('create table if not exists ci_sources(id text primary key, document text)')
        con.execute('create table if not exists ci_source_objects(key text primary key, data blob)')

    class Store(SQLitePlanStoreAdapter):
        def _request(self,method,path,payload=None,**kwargs):
            with sqlite3.connect(database) as con:
                if path.startswith(SOURCES.TABLE):
                    if method=='POST':
                        con.execute('insert or ignore into ci_sources values(?,?)',(payload['id'],json.dumps(payload)));return None
                    query=urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
                    documents=[json.loads(row[0]) for row in con.execute('select document from ci_sources')]
                    return [d for d in documents if d['project_id']==query['project_id'][0][3:] and ('id' not in query or d['id']==query['id'][0][3:])]
                if method != "GET" or not path.startswith("/rest/v1/acs_workspace_jobs?"):
                    raise AssertionError("Unexpected browser-fixture request")
                query = urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
                project_id = query["project_id"][0].removeprefix("eq.")
                job_id = query["id"][0].removeprefix("eq.")
                db.project_state(project_id, actor_id=ACTOR)
                row = con.execute("select document from ci_jobs where id=?", (job_id,)).fetchone()
                job = json.loads(row[0]) if row else None
                return [job] if job and job["project_id"] == project_id and job["created_by"] == ACTOR else []

        def _signed_rpc(self, name, kind, project_id, expected_head, document):
            # This SQLite fixture implements delivery receipts for browser tests.
            # Signature/expiry/RLS assertions run on real PostgreSQL independently.
            if (name, kind) != ("acs_workspace_job_mutate", "workspace_job"):
                raise AssertionError("Unexpected mutation in the connected browser fixture")
            db.project_state(project_id, actor_id=ACTOR)
            job_id, op = document["job_id"], document["operation"]
            with sqlite3.connect(database) as con:
                con.execute("begin immediate")
                row = con.execute("select document from ci_jobs where id=?", (job_id,)).fetchone()
                job = json.loads(row[0]) if row else None
                if job and (job["project_id"] != project_id or job["created_by"] != ACTOR):
                    raise H.PlanError("PROJECT_ACCESS_DENIED", "Fixture project mismatch")
                if op == "reserve":
                    if job:
                        if job["input_hash"] != document["input_hash"]:
                            raise H.PlanError("STALE_REVISION", "Fixture replay mismatch")
                        return {"created": False, "job": job}
                    job = {"id": job_id, "project_id": project_id, "created_by": ACTOR,
                           "expected_head": expected_head, "resume_command": document["command"],
                           "state": "RUNNING", "phase": "UNDERSTANDING", "provider_calls": 0,
                           "lease_token": document["lease_token"], "worker_id": document["worker_id"],
                           "input_hash": document["input_hash"]}
                    con.execute("insert into ci_jobs values (?,?)", (job_id, json.dumps(job)))
                    return {"created": True, "job": job}
                if not job:
                    raise H.PlanError("REVISION_NOT_FOUND", "Unknown fixture job")
                if op == "expire":
                    return {"job": job}  # No simulated clock expiry in this browser fixture.
                if op == "cancel":
                    if job["state"] == "RUNNING":
                        job.update(state="CANCELLED", error_code="PROVIDER_OUTCOME_UNKNOWN")
                else:
                    if job["state"] != "RUNNING" or document.get("lease_token") != job["lease_token"]:
                        raise H.PlanError("JOB_LEASE_LOST", "Fixture worker no longer owns this job")
                    if op == "heartbeat":
                        return {"job": job}
                    fields = {"progress": ("phase", "progress", "checkpoint", "provider_calls"),
                              "finish": ("state", "revision_id", "error_code")}
                    if op not in fields:
                        raise AssertionError("Unsupported browser-fixture job operation")
                    job.update({key: document[key] for key in fields[op] if key in document})
                con.execute("update ci_jobs set document=? where id=?", (json.dumps(job), job_id))
                return {"job": job}

    async def authorize(scope,send):
        headers=dict(scope.get('headers',[]))
        if headers.get(b'authorization') != b'Bearer fixture-access':
            await P._send_json(scope,send,401,{'ok':False,'error':{'code':'AUTH_REQUIRED','message':'Fixture authentication required'}});return False
        scope.setdefault('state',{})['authenticated_user_id']=ACTOR
        return True

    def gateway(method,path,**kwargs):
        if path.startswith('/auth/v1/token?'):
            return 200,{'access_token':'fixture-access','refresh_token':'fixture-refresh','expires_in':3600,'user':{'id':ACTOR,'email':'fixture@example.test'}}
        if path=='/auth/v1/user':return 200,{'id':ACTOR,'email':'fixture@example.test'}
        if path=='/rest/v1/acs_projects' and method=='POST':
            project={'id':str(uuid.uuid4()),'name':kwargs['payload']['name'],'owner_id':ACTOR}
            db.create_project(project['id'],owner_id=ACTOR);projects.append(project);return 201,[project]
        if path.startswith('/rest/v1/acs_projects?'):
            query=urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
            selected=query.get('id',[None])[0]
            rows=[p for p in projects if selected is None or selected=='eq.'+p['id']]
            return 200,rows[:1] if query.get('limit')==['1'] else rows
        if path=='/auth/v1/logout':return 200,{}
        raise AssertionError(path)

    AUTH.authorize_asgi=authorize
    def source_object(store,method,project_id,source_id,part,raw=None,media=None):
        db.project_state(project_id,actor_id=ACTOR)
        key='/'.join([project_id,source_id,part])
        with sqlite3.connect(database) as con:
            if method=='POST':con.execute('insert or ignore into ci_source_objects values(?,?)',(key,raw));return b''
            row=con.execute('select data from ci_source_objects where key=?',(key,)).fetchone()
            if not row:raise ValueError('Fixture source unavailable')
            return row[0]
    SOURCES.object_request=source_object
    SESSION.authenticated_supabase_plan_store=lambda scope:Store(db)
    G._request=gateway
    JOBS.default_runner=lambda:FixtureRunner(counts)
    app=FastAPI()
    @app.get('/test-stats')
    def stats():return counts
    @app.get('/test-diagnostics')
    def diagnostics():
        # This loopback-only synthetic server deliberately exposes no command,
        # source bytes, credentials, or provider payload in failure diagnostics.
        keys=('id','project_id','state','phase','revision_id','expected_head',
              'error_code','provider_calls','finished_at')
        with sqlite3.connect(database) as con:
            documents=[json.loads(row[0]) for row in con.execute(
                'select document from ci_jobs order by rowid desc limit 12')]
        return {'counts':dict(counts),'active_jobs':sorted(H.ACTIVE_JOBS),
                'pending_tasks':len(H.PAID_TASKS),
                'jobs':[{key:doc.get(key) for key in keys} for doc in documents]}
    @app.get('/health')
    def health():return {'ok':True,'api_key_configured':True}
    app.add_middleware(P.PlanCommandMiddleware)
    app.add_middleware(H.WorkspaceMiddleware)
    app.add_middleware(CORSMiddleware,allow_origins=['https://acs-ui.test'],allow_headers=['*'],allow_methods=['*'])
    return app


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--database',required=True);args=p.parse_args()
    uvicorn.run(application(args.database),host='127.0.0.1',port=args.port,log_level='warning')
