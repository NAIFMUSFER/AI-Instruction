#!/usr/bin/env python3
"""History transport admission, immutable recovery and signed backend writes."""
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_store import revision_document, approval_document
from acs_plan_store_reload import load_workspace
from acs_plan_review import PlanError
from acs_supabase_plan_store import SupabasePlanStore

ACTOR='11111111-1111-4111-8111-111111111111'
PROJECT='22222222-2222-4222-8222-222222222222'
SECRET='ab'*32


def make_docs(count,size):
    workspace=PlanLockWorkspace()
    docs=[]
    for i in range(count):
        revision=workspace.propose({'floors':{'g':{'rooms':[{'id':'room','rect':[0,0,4,4]}]}},
                                   'levels':[{'index':0,'template':'g'}],'test_note':'x'*size},
                                  brief='Synthetic',requirements=[],expected_head=workspace.head,note=str(i))
        docs.append(revision_document(revision))
    return docs,workspace


class FakeDB:
    def __init__(self,docs):
        self.docs=docs
        self.head=docs[-1]['revision_id'] if docs else None
        self.calls=[]
        self.max_response=0
        self.race=False
        self.denied=False
        self.corrupt=False
        self.bad_cursor=False
    def __call__(self,**kw):
        name=kw['url'].rsplit('/',1)[-1]
        payload=json.loads(kw['body'])
        self.calls.append((name,payload))
        meta=[{k:doc[k] for k in ('revision_id','number','parent_id','content_hash','bound_content_hash')} for doc in self.docs]
        if name=='acs_plan_workspace_snapshot':  # Baseline reproduction witness.
            response={'schema':'acs.plan-store-workspace-snapshot/1.0','project_id':PROJECT,
                      'head_revision_id':self.head,'baseline_revision_id':None,'revisions':self.docs,'approvals':[]}
        elif name=='acs_plan_revision_page':
            rows=meta[payload['p_after']:payload['p_after']+payload['p_limit']]
            next_after=payload['p_after']+len(rows)
            response={'schema':'acs.plan-revision-page/1.0','project_id':PROJECT,'role':'owner',
                      'head_revision_id':self.head,'baseline_revision_id':None,'revisions':rows,
                      'next_after':(0 if self.bad_cursor else next_after) if next_after<len(meta) else None}
        elif name=='acs_plan_revision_document':
            if self.denied:
                return 403,b'{}'
            doc=deepcopy(next(d for d in self.docs if d['revision_id']==payload['p_revision']))
            if self.corrupt:
                doc['model']['test_note']='altered'
            response={'schema':'acs.plan-revision-document/1.0','project_id':PROJECT,'revision':doc,'approval':None}
        elif name=='acs_plan_project_state':
            response={'schema':'acs.plan-store/1.0','project_id':PROJECT,'role':'owner',
                      'head_revision_id':'raced' if self.race else self.head,'baseline_revision_id':None,'revisions':meta}
        elif name=='acs_write_plan_receipt':
            raw=payload['p_payload']
            assert hmac.compare_digest(payload['p_signature'],hmac.new(SECRET.encode(),raw.encode(),hashlib.sha256).hexdigest())
            env=json.loads(raw)
            assert env['actor_id']==ACTOR and env['project_id']==PROJECT
            response=env['document']
        else:
            raise AssertionError('unexpected endpoint '+name)
        raw=json.dumps(response,ensure_ascii=False,separators=(',',':')).encode()
        self.max_response=max(self.max_response,len(raw))
        return 200,raw


def store(db,**kwargs):
    return SupabasePlanStore('https://example.supabase.co','synthetic-key','synthetic-jwt',actor_id=ACTOR,transport=db,**kwargs)


def denial(call,code):
    try: call()
    except PlanError as exc: assert exc.code==code,(exc.code,code)
    else: raise AssertionError('expected '+code)

# Five valid 650 kB models previously passed individual admission and broke reopen.
docs,workspace=make_docs(5,650_000)
db=FakeDB(docs)
restored=load_workspace(store(db),PROJECT,actor_id=ACTOR)
assert restored.head==workspace.head
assert [restored.get(d['revision_id']).model_hash for d in docs]==[d['model_hash'] for d in docs]
assert sum(len(json.dumps(d)) for d in docs)>3_000_000
assert db.max_response<700_000
assert sum(n=='acs_plan_revision_document' for n,_ in db.calls)==5
assert all(n!='acs_plan_workspace_snapshot' for n,_ in db.calls)
print('PASS: five 650 kB immutable revisions reopen; each response <700 kB')

# Crossing metadata page boundary must neither omit nor duplicate old revisions.
many,_=make_docs(26,0)
pages=FakeDB(many)
assert len(store(pages).workspace_snapshot(PROJECT,actor_id=ACTOR)['revisions'])==26
assert [p['p_after'] for n,p in pages.calls if n=='acs_plan_revision_page']==[0,25]
print('PASS: metadata keyset pagination crosses 25-row boundary')
for flag,code in [('race','STALE_REVISION'),('denied','PROJECT_ACCESS_DENIED'),('corrupt','STORED_MODEL_TAMPERED')]:
    fixture=FakeDB(docs);setattr(fixture,flag,True)
    denial(lambda:store(fixture).workspace_snapshot(PROJECT,actor_id=ACTOR),code)
fixture=FakeDB(many);fixture.bad_cursor=True
denial(lambda:store(fixture).workspace_snapshot(PROJECT,actor_id=ACTOR),'STORED_PROJECT_TAMPERED')
print('PASS: changed head, revoked membership, tampered model and stalled cursor fail closed')

# Missing signer cannot accidentally downgrade to legacy writable RPCs.
fixture=FakeDB([])
denial(lambda:store(fixture,write_secret='').save_revision(PROJECT,actor_id=ACTOR,revision=workspace.get(workspace.head),expected_head=docs[-1]['parent_id']),'STORE_UNAVAILABLE')
assert not fixture.calls
signed_store=store(fixture,write_secret=SECRET)
signed_store._lease_context={'job_id':'synthetic-job','lease_token':'synthetic-lease'}
assert signed_store.save_revision(PROJECT,actor_id=ACTOR,revision=workspace.get(workspace.head),expected_head=docs[-1]['parent_id'])==docs[-1]
name,payload=fixture.calls[-1]
assert name=='acs_write_plan_receipt'
env=json.loads(payload['p_payload'])
assert env['write_context']==signed_store._lease_context
assert env['kind']=='revision' and env['expected_head']==docs[-1]['parent_id']
assert SECRET not in json.dumps(fixture.calls)
# A forged receipt fails before signing/network; the authenticated client cannot
# produce a valid server capability or persist self-consistent fake hashes.
forged=SimpleNamespace(**{key:getattr(workspace.get(workspace.head),key) for key in
 ('id','number','parent_id','model','requirements_json','brief','note','locked_rooms','created_at',
  'model_hash','content_hash','semantic_lock_manifest','semantic_lock_manifest_hash','semantic_lock_count','bound_content_hash')})
forged.model_hash='0'*64
before=len(fixture.calls)
denial(lambda:signed_store.save_revision(PROJECT,actor_id=ACTOR,revision=forged,expected_head=docs[-1]['parent_id']),'STORED_MODEL_TAMPERED')
assert len(fixture.calls)==before
print('PASS: exact backend capability scope, no downgrade, malformed receipt rejected before signing')
print('ACS paged history and validated writes: PASS')
