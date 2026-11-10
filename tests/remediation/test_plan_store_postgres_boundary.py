#!/usr/bin/env python3
"""Execute real PostgreSQL migration/RBAC regressions without a network socket.

Uses an isolated synthetic cluster, never the configured production database.
PG_BINDIR=/usr/lib/postgresql/16/bin python ...; pgserver is an optional binary
source. --baseline omits remediation and MUST fail the authorization regression.
Missing PostgreSQL is NOT VERIFIED (exit 2), never a success.
"""
from pathlib import Path
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from acs_plan_lock_binding import PlanLockWorkspace
from acs_plan_store import revision_document

ACTOR = "11111111-1111-4111-8111-111111111111"
EDITOR = "22222222-2222-4222-8222-222222222222"
VIEWER = "33333333-3333-4333-8333-333333333333"
OTHER = "44444444-4444-4444-8444-444444444444"
PROJECT = "55555555-5555-4555-8555-555555555555"
OTHER_PROJECT = "66666666-6666-4666-8666-666666666666"
MISSING = "77777777-7777-4777-8777-777777777777"
SECRET = "ab" * 32  # Synthetic test-only value, never a production credential.


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def json_sql(value):
    return quote(json.dumps(value, ensure_ascii=False, separators=(",", ":"))) + "::jsonb"


def signed(kind, doc, actor=ACTOR, project=PROJECT, head=None, **overrides):
    env = {"schema": "acs.validated-write/1.0", "kind": kind, "actor_id": actor,
           "project_id": project, "expected_head": head, "document": doc,
           "expires_at": int(time.time()) + 90, "write_context": None}
    env.update(overrides)
    raw = json.dumps(env, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    sig = hmac.new(SECRET.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return "public.acs_write_plan_receipt(%s,%s)" % (quote(raw), quote(sig))


def bindir():
    configured = os.environ.get("PG_BINDIR")
    if configured:
        return Path(configured)
    for path in sorted(Path("/usr/lib/postgresql").glob("*/bin"), reverse=True):
        if (path / "postgres").is_file():
            return path
    try:
        import pgserver
        return Path(pgserver.__file__).parent / "pginstall/bin"
    except ImportError:
        print("NOT VERIFIED: PostgreSQL binaries unavailable; set PG_BINDIR")
        sys.exit(2)


counter = 0

def expect_denied(expr, label):
    global counter
    counter += 1
    return """do $test$ declare denied boolean:=false; begin
      begin perform %s; exception when others then
        if sqlstate not in ('P0001','42501') then raise; end if;
        denied:=true;
      end;
      if not denied then raise exception 'SECURITY_REGRESSION: %s'; end if;
      raise notice 'PASS %s'; end $test$;""" % (expr, label, label)


def expect(expr, label):
    global counter
    counter += 1
    return "do $test$ begin if not coalesce((%s),false) then raise exception 'ASSERT: %s'; end if; raise notice 'PASS %s'; end $test$;" % (expr, label, label)


def as_user(actor, sql, role="authenticated"):
    return "set role %s; select set_config('request.jwt.claim.sub',%s,false);\n%s\nreset role;\n" % (role, quote(actor), sql)


def main():
    binary = bindir()
    with tempfile.TemporaryDirectory(prefix="acs-db-test-") as temp:
        data = Path(temp) / "data"
        init = subprocess.run([str(binary / "initdb"), "-D", str(data), "--auth=trust", "--no-locale", "--encoding=UTF8"], capture_output=True, text=True)
        if init.returncode:
            print("NOT VERIFIED: PostgreSQL initdb failed", init.stderr[-2000:])
            return 2
        def execute(sql, label):
            # -j accepts complete multi-line SQL until a blank line. Individual
            # function bodies retain newlines; remove blank lines, not comments.
            sql = "\n".join(line for line in sql.splitlines() if line.strip()) + "\n\n"
            done = subprocess.run([str(binary / "postgres"), "--single", "-j", "-D", str(data), "postgres"], input=sql, capture_output=True, text=True)
            output = done.stdout + done.stderr
            # Standalone PostgreSQL can exit 0 after SQL errors: enforce evidence.
            if done.returncode or any(mark in output for mark in ("ERROR:", "FATAL:", "PANIC:")):
                print("FAIL", label)
                print(output[-18000:])
                return False
            for line in done.stderr.splitlines():
                if "NOTICE:  PASS" in line:
                    print(line.split("NOTICE:  ", 1)[1])
            return True
        setup = """
        create role anon; create role authenticated;
        create schema auth;
        create table auth.users(id uuid primary key);
        create function auth.uid() returns uuid language sql stable as $$
          select nullif(current_setting('request.jwt.claim.sub',true),'')::uuid $$;
        grant usage on schema auth to anon,authenticated;
        grant execute on function auth.uid() to anon,authenticated;
        create schema storage;
        create table storage.buckets(id text primary key,name text,public boolean,file_size_limit bigint,allowed_mime_types text[]);
        create table storage.objects(id uuid,name text,bucket_id text);
        alter table storage.objects enable row level security;
        create function storage.foldername(text) returns text[] language sql immutable as $$ select string_to_array($1,'/') $$;
        """
        if not execute(setup, "synthetic auth/storage setup"):
            return 1
        paths = list((ROOT / "supabase/migrations").glob("*.sql"))
        # Legacy filenames predate sortable timestamp conventions.
        early = ["20260912_acs_plan_store_v2.sql", "20260912_acs_plan_store_v2_harden_functions.sql", "20260913_acs_plan_store_rpc_v2.sql", "20260913_acs_plan_store_rpc_v2_lockdown.sql"]
        paths.sort(key=lambda p: (0, early.index(p.name)) if p.name in early else (1, p.name))
        for path in paths:
            if any(x.startswith("--baseline") for x in sys.argv) and path.name.startswith("20261110"):
                continue
            if not execute(path.read_text(), path.name):
                return 1
            if path.name == "2026111001_acs_plan_boundary_and_history.sql":
                if not execute("insert into acs_private.acs_backend_write_keys(name,secret) values ('v1',%s);" % quote(SECRET), "synthetic signer provision"):
                    return 1
        fixtures = "insert into auth.users values %s;" % ",".join("(%s)" % quote(x) for x in [ACTOR, EDITOR, VIEWER, OTHER])
        fixtures += "insert into public.acs_projects(id,owner_id,name) values (%s,%s,'Synthetic one'),(%s,%s,'Synthetic two');" % tuple(map(quote, [PROJECT, ACTOR, OTHER_PROJECT, OTHER]))
        fixtures += "insert into public.acs_project_members(project_id,user_id,role) values (%s,%s,'editor'),(%s,%s,'viewer');" % tuple(map(quote, [PROJECT, EDITOR, PROJECT, VIEWER]))
        if not execute(fixtures, "synthetic fixtures"):
            return 1
        if "--baseline-direct" in sys.argv:
            malformed = {"revision_id":"bad","number":1,"parent_id":None,"model_hash":"a"*64,"content_hash":"a"*64,"bound_content_hash":"a"*64,"created_at":"2026-11-10T00:00:00Z"}
            witness=as_user(EDITOR,expect_denied("public.acs_save_plan_revision(%s,null,%s)" % (quote(PROJECT),json_sql(malformed)), "malformed direct revision rejected"))
            if not execute(witness,"direct RPC validation regression"):
                return 1
            print("Unexpected baseline direct-write pass")
            return 1
        # First regression fails on reviewed legacy SQL because NULL NOT IN is NULL.
        first = as_user(OTHER, expect_denied("public.acs_plan_project_state(%s)" % quote(PROJECT), "nonmember read denied"))
        if not execute(first, "membership regression"):
            return 1
        if "--baseline" in sys.argv:
            print("Unexpected baseline pass: investigate before claiming reproduced")
            return 1
        sql = ""
        # RFC vectors and independent Python known outputs, short/long keys, UTF8.
        for key, message in [("key", "The quick brown fox jumps over the lazy dog"), ("x" * 131, "long key"), ("ab" * 32, "مستودع 🏗️"), ("", "")]:
            expected = hmac.new(key.encode(), message.encode(), hashlib.sha256).hexdigest()
            sql += expect("acs_private.acs_hmac_sha256(%s,%s)=%s" % (quote(message), quote(key), quote(expected)), "HMAC vector %d" % len(message))
        sql += as_user("", expect_denied("public.acs_plan_project_state(%s)" % quote(PROJECT), "anonymous denied"), role="anon")
        for who in [ACTOR, EDITOR, VIEWER]:
            sql += as_user(who, expect("public.acs_plan_project_state(%s)->>'project_id'=%s" % (quote(PROJECT),quote(PROJECT)), "legitimate role read " + who[:4]))
        sql += as_user(OTHER, expect_denied("public.acs_plan_project_state(%s)" % quote(MISSING), "nonexistent indistinguishable denial"))
        sql += as_user(OTHER, expect("acs_private.acs_is_project_owner(%s,%s) is false" % (quote(PROJECT),quote(ACTOR)), "ownership helper reveals no other actor relation"))
        sql += as_user(ACTOR, expect_denied("(select secret from acs_private.acs_backend_write_keys limit 1)", "signer key not readable"))
        malformed = {"revision_id":"bad","number":1,"parent_id":None,"model_hash":"a"*64,"content_hash":"a"*64,"bound_content_hash":"a"*64,"created_at":"2026-11-10T00:00:00Z"}
        for who in [ACTOR, EDITOR, VIEWER, OTHER]:
            for namespace in ["public", "acs_private"]:
                sql += as_user(who, expect_denied("%s.acs_save_plan_revision(%s,null,%s)" % (namespace,quote(PROJECT),json_sql(malformed)), "direct revision bypass denied " + who[:4] + namespace))
                sql += as_user(who, expect_denied("%s.acs_save_plan_approval(%s,'bad',%s)" % (namespace,quote(PROJECT),json_sql(malformed)), "direct approval bypass denied " + who[:4] + namespace))
        sql += as_user(EDITOR, expect_denied("public.acs_write_plan_receipt('{}',%s)" % quote("0"*64), "forged signature denied"))
        ws=PlanLockWorkspace()
        revision=ws.propose({"levels":[],"floors":{}},brief="Synthetic",requirements=[],expected_head=None,note="Initial")
        doc=revision_document(revision)
        valid=signed("revision",doc)
        sql += as_user(ACTOR, expect_denied(signed("workspace_job",doc), "capability purpose substitution denied"))
        sql += as_user(EDITOR, expect_denied(valid, "signed identity substitution denied"))
        sql += as_user(ACTOR, expect_denied(signed("revision", doc, expires_at=0), "expired capability denied"))
        sql += as_user(ACTOR, expect_denied(signed("revision", doc, expires_at=int(time.time())+3600), "unbounded expiry denied"))
        sql += as_user(ACTOR, expect_denied(signed("revision", doc, project=OTHER_PROJECT), "cross project capability denied"))
        sql += as_user(VIEWER, expect_denied(signed("revision", doc, actor=VIEWER), "viewer signed write denied"))
        sql += as_user(ACTOR, expect("(%s)->>'revision_id'=%s" % (valid,quote(revision.id)), "validated owner append succeeds"))
        sql += as_user(ACTOR, expect_denied(valid, "revision replay leaves head immutable"))
        sql += as_user(ACTOR, expect_denied(signed("revision",{**doc,"revision_id":"bad2","number":2,"parent_id":revision.id},head="wrong"), "stale head denied"))
        sql += as_user(ACTOR, expect_denied("public.acs_plan_revision_document(%s,%s,%s)" % (quote(OTHER_PROJECT),quote(revision.id),quote(revision.id)), "cross project revision denied"))
        sql += as_user(ACTOR, expect("jsonb_array_length(public.acs_plan_revision_page(%s,0,1,null)->'revisions')=1" % quote(PROJECT), "bounded metadata read"))
        sql += as_user(ACTOR, expect_denied("public.acs_plan_revision_page(%s,0,26,null)" % quote(PROJECT), "oversized metadata page denied"))
        approval={"schema":"acs.plan-store-approval/1.0","revision_id":revision.id,"revision_content_hash":doc["content_hash"],"bound_content_hash":doc["bound_content_hash"],"model_hash":doc["model_hash"],"semantic_lock_manifest_hash":None,"semantic_lock_count":0,"actor_label":"Synthetic owner","approved_at":"2026-11-10T00:00:00Z","scope":"CONCEPTUAL_DESIGN_ONLY"}
        sql += as_user(ACTOR, expect_denied(signed("approval",{**approval,"model_hash":"0"*64},head=revision.id), "forged approval hash denied"))
        sql += as_user(ACTOR, expect_denied(signed("approval",{**approval,"scope":"STRUCTURAL"},head=revision.id), "approval scope denied"))
        sql += as_user(ACTOR, expect("(%s)->>'revision_id'=%s" % (signed("approval",approval,head=revision.id),quote(revision.id)), "validated approval succeeds"))
        sql += as_user(ACTOR, expect_denied(signed("approval",approval,head=revision.id), "approval replay denied"))
        next_revision=ws.propose({"levels":[],"floors":{}},brief="Synthetic",requirements=[],expected_head=ws.head,note="Editor update")
        next_doc=revision_document(next_revision)
        sql += as_user(OTHER, expect_denied(signed("revision",next_doc,actor=OTHER,project=OTHER_PROJECT), "cross project parent denied"))
        sql += as_user(OTHER, expect_denied(signed("approval",approval,actor=OTHER,project=OTHER_PROJECT,head=revision.id), "cross project approval denied"))
        sql += as_user(EDITOR, expect("(%s)->>'revision_id'=%s" % (signed("revision",next_doc,actor=EDITOR,head=revision.id),quote(next_revision.id)), "validated editor append succeeds"))
        sql += "delete from public.acs_project_members where project_id=%s and user_id=%s;" % (quote(PROJECT),quote(EDITOR))
        sql += as_user(EDITOR, expect_denied("public.acs_plan_project_state(%s)" % quote(PROJECT), "removed member read denied"))
        sql += as_user(EDITOR, expect_denied(signed("revision", doc, actor=EDITOR), "removed member write denied"))
        sql += expect("(select count(*)=2 from public.acs_plan_revisions where project_id=%s)" % quote(PROJECT), "rejected writes leave history unchanged")
        sql += expect("(select head_revision_id=%s and baseline_revision_id=%s from public.acs_projects where id=%s)" % tuple(map(quote,[next_revision.id,revision.id,PROJECT])), "head and baseline remain exact")
        # Every executable definer has an explicit pinned path; no default PUBLIC execution.
        sql += expect("not exists(select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname in ('public','acs_private') and p.prosecdef and not exists(select 1 from unnest(p.proconfig) c where c like 'search_path=%%'))", "all definers pin search path")
        if not execute(sql, "adversarial SQL boundary"):
            return 1
        extension = os.environ.get("ACS_SQL_TEST_EXTENSION")
        if extension and not execute(Path(extension).read_text(), "additional PostgreSQL behavior assertions"):
            return 1
        print("ACS PostgreSQL boundary: PASS (%d assertions; real PostgreSQL, synthetic users/projects)" % counter)
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
