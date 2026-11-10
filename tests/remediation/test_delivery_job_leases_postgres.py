#!/usr/bin/env python3
"""Real PostgreSQL lease/fencing/idempotency tests with synthetic-only data."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import uuid
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_plan_store_postgres_boundary as DB
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_store import revision_document

PROJECT='88888888-8888-4888-8888-888888888888'
JOB='99999999-9999-4999-8999-999999999999'
SECOND='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
THIRD='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
FOURTH='cccccccc-cccc-4ccc-8ccc-cccccccccccc'
FIFTH='12345678-1234-4234-8234-123456789abc'
LEASE='dddddddd-dddd-4ddd-8ddd-dddddddddddd'
WRONG='eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'
WORKER='ffffffff-ffff-4fff-8fff-ffffffffffff'
HASH='a'*64


def mutation(op,job=JOB,actor=DB.ACTOR,head=None,**fields):
    doc={'operation':op,'job_id':job,**fields}
    return DB.signed('workspace_job',doc,actor=actor,project=PROJECT,head=head).replace('public.acs_write_plan_receipt','public.acs_workspace_job_mutate')


def command(job=JOB,**fields):
    return {'action':'generate','job_id':job,'confirmed':True,'max_provider_calls':3,'expected_head':None,**fields}


def reserve(job=JOB,**fields):
    return mutation('reserve',job=job,input_hash=HASH,worker_id=WORKER,lease_token=LEASE,command=command(job,**fields))


def main():
    sql="insert into public.acs_projects(id,owner_id,name) values (%s,%s,'Synthetic lease fixtures');" % (DB.quote(PROJECT),DB.quote(DB.ACTOR))
    sql+="insert into public.acs_project_members(project_id,user_id,role) values (%s,%s,'viewer');" % (DB.quote(PROJECT),DB.quote(DB.VIEWER))
    sql+=DB.expect("not has_table_privilege('authenticated','public.acs_workspace_jobs','INSERT')",'jobs direct insertion revoked')
    sql+=DB.expect("not has_column_privilege('authenticated','public.acs_workspace_jobs','provider_calls','UPDATE')",'budget tampering revoked')
    sql+=DB.as_user(DB.VIEWER,DB.expect_denied(mutation('reserve',actor=DB.VIEWER,command=command(),input_hash=HASH,worker_id=WORKER,lease_token=LEASE),'viewer cannot reserve paid work'))
    sql+=DB.as_user(DB.OTHER,DB.expect_denied(mutation('reserve',actor=DB.OTHER,command=command(),input_hash=HASH,worker_id=WORKER,lease_token=LEASE),'nonmember cannot reserve paid work'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('reserve',command=command(confirmed=False),input_hash=HASH,worker_id=WORKER,lease_token=LEASE),'missing confirmation blocked at actual mutation boundary'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'created'='true'" % reserve(),'first reservation starts once'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'created'='false'" % reserve(),'same job replay does not start another worker'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('reserve',command=command(),input_hash='b'*64,worker_id=WORKER,lease_token=LEASE),'changed replay denied'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(reserve(SECOND),'healthy project lease blocks second paid worker'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='RUNNING'" % mutation('expire'),'polling healthy lease preserves running state'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('heartbeat',lease_token=WRONG),'wrong worker lease fenced'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='RUNNING'" % mutation('heartbeat',lease_token=LEASE),'correct heartbeat succeeds'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'provider_calls'='2'" % mutation('progress',lease_token=LEASE,provider_calls=2,phase='LAYOUT',checkpoint={'kind':'outline'}),'spent calls persisted'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('progress',lease_token=LEASE,provider_calls=1),'spent budget cannot decrease'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('progress',lease_token=LEASE,provider_calls=4),'spent budget cannot exceed authorization'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='CANCELLED'" % mutation('cancel'),'cancellation atomically fences lease'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('heartbeat',lease_token=LEASE),'cancelled worker cannot revive job'))
    ws=PlanLockWorkspace();revision=ws.propose({'levels':[],'floors':{}},brief='Synthetic lease',requirements=[],expected_head=None,note='task:'+JOB)
    doc=revision_document(revision)
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(DB.signed('revision',doc,project=PROJECT,write_context={'job_id':JOB,'lease_token':LEASE}),'late cancelled canonical append fenced'))
    sql+=DB.expect("not exists(select 1 from public.acs_plan_revisions where project_id=%s)"%DB.quote(PROJECT),'cancelled append leaves immutable history unchanged')
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'created'='true'" % reserve(SECOND),'new explicit operation can start after cancellation'))
    sql+="update public.acs_workspace_jobs set lease_expires_at=clock_timestamp()-interval '1 second' where id=%s;"%DB.quote(SECOND)
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='INTERRUPTED'" % mutation('expire',job=SECOND),'expired worker becomes interrupted by database clock'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(reserve(THIRD,resume_job_id=SECOND),'uncertain expired provider call cannot resume'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('finish',job=SECOND,lease_token=LEASE,state='FAILED',error_code='KNOWN_FAILURE'),'late completion cannot overwrite interrupted state'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'created'='true'" % reserve(THIRD),'next explicitly authorized operation starts'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='FAILED'" % mutation('finish',job=THIRD,lease_token=LEASE,state='FAILED',error_code='PLAN_DETAIL_INCOMPLETE'),'known completed failure permits explicit recovery'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'created'='true'" % reserve(FOURTH,resume_job_id=THIRD),'one explicit resume consumes saved task'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='FAILED'" % mutation('finish',job=FOURTH,lease_token=LEASE,state='FAILED',error_code='PLAN_DETAIL_INCOMPLETE'),'resumed attempt finishes'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(reserve(WRONG,resume_job_id=THIRD),'same source checkpoint cannot be resumed twice'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'created'='true'" % reserve(FIFTH),'active new job ready to append'))
    goodws=PlanLockWorkspace();goodrevision=goodws.propose({'levels':[],'floors':{}},brief='Synthetic completed lease',requirements=[],expected_head=None,note='task:'+FIFTH)
    gooddoc=revision_document(goodrevision)
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(DB.signed('revision',doc,project=PROJECT,write_context={'job_id':FIFTH,'lease_token':LEASE}),'wrong task marker cannot claim leased append'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(DB.signed('revision',gooddoc,project=PROJECT,head='stale',write_context={'job_id':FIFTH,'lease_token':LEASE}),'lease expected revision must match canonical append'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->>'revision_id'=%s" % (DB.signed('revision',gooddoc,project=PROJECT,write_context={'job_id':FIFTH,'lease_token':LEASE}),DB.quote(goodrevision.id)),'active lease canonical append succeeds'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='SUCCEEDED'" % mutation('finish',job=FIFTH,lease_token=LEASE,state='SUCCEEDED',revision_id=goodrevision.id),'job completion bound to exact canonical task revision'))
    sql+=DB.as_user(DB.ACTOR,DB.expect_denied(mutation('heartbeat',job=FIFTH,lease_token=LEASE),'terminal success cannot be restarted'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='SUCCEEDED'" % mutation('cancel',job=FIFTH),'cancellation after canonical commit preserves success'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='SUCCEEDED'" % mutation('expire',job=FIFTH),'postcommit expiry polling preserves success'))
    sql+=DB.as_user(DB.ACTOR,DB.expect("(%s)->'job'->>'state'='SUCCEEDED'" % mutation('finish',job=FIFTH,lease_token=LEASE,state='SUCCEEDED',revision_id=goodrevision.id),'same terminal receipt completion is idempotent'))
    count=DB.counter
    with tempfile.TemporaryDirectory(prefix='acs-job-sql-') as directory:
        script=Path(directory)/'lease-tests.sql';script.write_text(sql)
        env=dict(os.environ,ACS_SQL_TEST_EXTENSION=str(script))
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('test_plan_store_postgres_boundary.py'))],env=env)
        if result.returncode:return result.returncode
    print(f'ACS PostgreSQL job leases: PASS ({count} real SQL assertions)')
    return 0

if __name__=='__main__':raise SystemExit(main())
