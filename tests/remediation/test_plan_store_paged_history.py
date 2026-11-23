#!/usr/bin/env python3
"""History transport admission, immutable recovery and signed backend writes."""
import hashlib
import hmac
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_store import revision_document
from acs_plan_store_reload import load_workspace
from test_rls_history_transport import HistoryTransport
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


class SignedWriteTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        name = kwargs["url"].rsplit("/", 1)[-1]
        payload = json.loads(kwargs["body"])
        assert name == "acs_write_plan_receipt" and kwargs["method"] == "POST"
        self.calls.append((name, payload))
        raw = payload["p_payload"]
        mac = hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()
        assert hmac.compare_digest(payload["p_signature"], mac)
        envelope = json.loads(raw)
        assert envelope["actor_id"] == ACTOR and envelope["project_id"] == PROJECT
        return 200, json.dumps(envelope["document"], separators=(",", ":")).encode()


def store(db,**kwargs):
    return SupabasePlanStore('https://example.supabase.co','synthetic-key','synthetic-jwt',actor_id=ACTOR,transport=db,**kwargs)


def denial(call,code):
    try: call()
    except PlanError as exc: assert exc.code==code,(exc.code,code)
    else: raise AssertionError('expected '+code)

# Five valid 650 kB models previously passed individual admission and broke reopen.
docs,workspace=make_docs(5,650_000)
db = HistoryTransport(docs)
restored = load_workspace(store(db), PROJECT, actor_id=ACTOR)
assert restored.head == workspace.head
assert [restored.get(d["revision_id"]).model_hash for d in docs] == [d["model_hash"] for d in docs]
assert sum(len(json.dumps(d)) for d in docs) > 3_000_000 and db.max_bytes < 700_000
print("PASS: signed-write adapter reopens five large RLS-protected immutable revisions")

# A stale gateway/cache that repeats page one cannot silently duplicate history.
many, _ = make_docs(26, 0)
class RepeatedPage(HistoryTransport):
    def __call__(self, **kwargs):
        kwargs["url"] = kwargs["url"].replace("revisions.revision_number=gt.25",
                                             "revisions.revision_number=gt.0")
        return super().__call__(**kwargs)

denial(lambda: store(RepeatedPage(many)).workspace_snapshot(PROJECT, actor_id=ACTOR),
       "INVALID_REVISION_CHAIN")

# Missing signer cannot accidentally downgrade to legacy writable RPCs.
fixture=SignedWriteTransport()
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
