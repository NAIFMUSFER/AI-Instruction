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
import acs_plan_session as SESSION
import acs_generation_job as JOBS
from acs_plan_store import SQLitePlanStore
from acs_plan_store_port import SQLitePlanStoreAdapter
from test_connected_workspace import PROJECT, ACTOR, model


def application(database):
    db=SQLitePlanStore(database)
    try:db.create_project(PROJECT,owner_id=ACTOR)
    except Exception:pass
    counts={'generation':0,'chat':0}
    projects=[{'id':PROJECT,'name':'مشروع التحقق','owner_id':ACTOR}]
    with sqlite3.connect(database) as con:con.execute('create table if not exists ci_jobs(id text primary key, document text)')

    class Store(SQLitePlanStoreAdapter):
        def _request(self,method,path,payload=None,**kwargs):
            with sqlite3.connect(database) as con:
                if method=='POST':
                    cur=con.execute('insert or ignore into ci_jobs values(?,?)',(payload['id'],json.dumps(payload)))
                    return [copy.deepcopy(payload)] if cur.rowcount else []
                query=urllib.parse.parse_qs(urllib.parse.urlsplit(path).query)
                job_id=query['id'][0].removeprefix('eq.')
                row=con.execute('select document from ci_jobs where id=?',(job_id,)).fetchone()
                if not row:return []
                data=json.loads(row[0])
                if method=='PATCH':
                    data.update(payload);con.execute('update ci_jobs set document=? where id=?',(json.dumps(data),job_id))
                return [data]

    class FixtureRunner:
        def run(self,target,kwargs,**controls):
            if target.endswith('generate_plan_candidate'):
                counts['generation']+=1;time.sleep(1.2)
                return {'building':model('warehouse' if 'مستودع' in kwargs['brief'] else 'residential'),'provider_calls':1}
            if target.endswith('budgeted_chat_candidate'):
                counts['chat']+=1
                candidate=copy.deepcopy(kwargs['building']);candidate['floors']['ground']['rooms'][1]['rect'][2]=6
                return candidate
            if target.endswith('artifact_from_snapshot'):return S.artifact_from_snapshot(**kwargs)
            raise AssertionError(target)

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
    SESSION.authenticated_supabase_plan_store=lambda scope:Store(db)
    G._request=gateway
    JOBS.default_runner=lambda:FixtureRunner()
    app=FastAPI()
    @app.get('/test-stats')
    def stats():return counts
    @app.get('/health')
    def health():return {'ok':True,'api_key_configured':True}
    app.add_middleware(P.PlanCommandMiddleware)
    app.add_middleware(H.WorkspaceMiddleware)
    app.add_middleware(CORSMiddleware,allow_origins=['https://acs-ui.test'],allow_headers=['*'],allow_methods=['*'])
    return app


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--database',required=True);args=p.parse_args()
    uvicorn.run(application(args.database),host='127.0.0.1',port=args.port,log_level='warning')
