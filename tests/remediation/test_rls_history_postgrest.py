"""Read an approved, multi-page fixture through PostgREST on a disposable loopback DB."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_review import PlanError
from acs_plan_store import approval_document, revision_document
from acs_plan_store_reload import load_workspace
from acs_supabase_plan_store import SupabasePlanStore
from test_plan_store_reload import reqs, verifier, warehouse

ROOT = Path(__file__).resolve().parents[2]
OWNER = "11111111-1111-4111-8111-111111111111"
VIEWER = "22222222-2222-4222-8222-222222222222"
OTHER = "33333333-3333-4333-8333-333333333333"
PROJECT = "44444444-4444-4444-8444-444444444444"
LOCAL_API = "http://127.0.0.1:55330"
TEST_ISSUER = b"isolated-postgrest-test-issuer-no-production-use"


def sql(statement):
    subprocess.run(["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1",
                    "-p", "55329", "-U", "postgres", "-d", "acs_history_fixture"],
                   input=statement, text=True, check=True)


def prepare():
    # CI supplies an empty test database. Existing schemas cause a hard failure.
    sql("""
      create role anon; create role authenticated;
      create role acs_history_api login password 'isolated-api-role';
      grant authenticated,anon to acs_history_api;
      create schema auth; create table auth.users (id uuid primary key);
      create function auth.uid() returns uuid language sql stable as $$
        select (nullif(current_setting('request.jwt.claims',true),'')::jsonb->>'sub')::uuid $$;
      grant usage on schema auth to anon,authenticated;
    """)
    for name in ["20260912_acs_plan_store_v2", "20260912_acs_plan_store_v2_harden_functions",
                 "20260913_acs_plan_store_rpc_v2", "20260913_acs_plan_store_rpc_v2_lockdown",
                 "20260914035029_acs_project_owner_returning"]:
        sql((ROOT / "supabase/migrations" / (name + ".sql")).read_text())
    sql(f"""insert into auth.users values ('{OWNER}'),('{VIEWER}'),('{OTHER}');
      insert into acs_projects(id,owner_id,name) values ('{PROJECT}','{OWNER}','Synthetic');
      insert into acs_project_members(project_id,user_id,role) values ('{PROJECT}','{VIEWER}','viewer');""")
    ws = PlanLockWorkspace(verifier=verifier)
    for number in range(26):
        model = warehouse()
        if number < 5:
            model["test_note"] = "x" * 650_000
        revision = ws.propose(model, brief="site width 30 warehouse", requirements=reqs(),
                              expected_head=ws.head, note=f"Synthetic revision {number}")
        doc = json.dumps(revision_document(revision), ensure_ascii=False, separators=(",", ":"))
        sql(f"""insert into acs_plan_revisions(project_id,revision_id,revision_number,parent_revision_id,
          revision_json,model_hash,content_hash,bound_content_hash,created_by,created_at)
          select '{PROJECT}',d->>'revision_id',(d->>'number')::int,d->>'parent_id',d,d->>'model_hash',
          d->>'content_hash',d->>'bound_content_hash','{OWNER}',(d->>'created_at')::timestamptz
          from (select $fixture${doc}$fixture$::jsonb) t(d);""")
    approval = ws.approve(ws.head, expected_head=ws.head, actor_label="Synthetic designer",
                          confirmed=True, acknowledge_concept_only=True)
    doc = json.dumps(approval_document(approval), ensure_ascii=False, separators=(",", ":"))
    sql(f"""insert into acs_plan_approvals(project_id,revision_id,approval_json,revision_content_hash,
      bound_content_hash,model_hash,approved_by,approved_at)
      select '{PROJECT}',d->>'revision_id',d,d->>'revision_content_hash',d->>'bound_content_hash',
      d->>'model_hash','{OWNER}',(d->>'approved_at')::timestamptz
      from (select $fixture${doc}$fixture$::jsonb) t(d);
      update acs_projects set head_revision_id='{ws.head}',baseline_revision_id='{ws.head}' where id='{PROJECT}';""")


def client(subject):
    # A separate test issuer signs test identities for this local API only.
    def b64(data):
        return base64.urlsafe_b64encode(data).decode().rstrip("=")
    claims = {"sub": subject, "role": "authenticated", "exp": int(time.time()) + 120}
    body = b64(b'{"alg":"HS256","typ":"JWT"}') + "." + b64(json.dumps(claims).encode())
    token = body + "." + b64(hmac.new(TEST_ISSUER, body.encode(), hashlib.sha256).digest())

    def local_transport(*, method, url, headers, body, timeout):
        path = url.removeprefix("https://fixture.invalid/rest/v1")
        request = Request(LOCAL_API + path, method=method, headers=headers, data=body)
        try:
            with urlopen(request, timeout=timeout) as response:
                return response.status, response.read(3_000_001)
        except HTTPError as exc:
            return exc.code, exc.read(3_000_001)
    return SupabasePlanStore("https://fixture.invalid", "fixture", token, actor_id=subject,
                             transport=local_transport)


def verify():
    for attempt in range(30):
        try:
            with urlopen(LOCAL_API, timeout=2):
                break
        except URLError:
            if attempt == 29:
                raise
            time.sleep(1)
    restored = load_workspace(client(OWNER), PROJECT, actor_id=OWNER, verifier=verifier)
    assert len(restored.history()) == 26 and restored.head == restored.baseline
    assert client(VIEWER).project_state(PROJECT, actor_id=VIEWER)["role"] == "viewer"
    for subject in (VIEWER, OTHER):
        try:
            client(subject).workspace_snapshot(PROJECT, actor_id=subject)
        except PlanError as exc:
            assert exc.code == "PROJECT_ACCESS_DENIED", exc.code
        else:
            raise AssertionError("Expected writable workspace access to be denied")
    print("PASS: PostgREST reloads approved 26-revision history, protects two distinct roles")


if __name__ == "__main__":
    {"prepare": prepare, "verify": verify}[sys.argv[1]]()
