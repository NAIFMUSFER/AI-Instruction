#!/usr/bin/env python3
"""Plan RPC membership checks fail closed on real PostgreSQL.

Applies every migration in supabase/migrations to an isolated, socket-less
cluster (`postgres --single`) with synthetic auth/storage stubs and synthetic
users, then calls the PostgREST-exposed plan RPCs as a non-member, a viewer,
an editor, the owner and an anonymous caller. Never touches a configured
database. Missing PostgreSQL, or initdb refusing to run (for example as root),
is NOT VERIFIED (exit 2), never a success.

    PG_BINDIR=/usr/lib/postgresql/16/bin python tests/remediation/test_plan_rpc_membership_postgres.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OWNER = "11111111-1111-4111-8111-111111111111"
EDITOR = "22222222-2222-4222-8222-222222222222"
VIEWER = "33333333-3333-4333-8333-333333333333"
STRANGER = "44444444-4444-4444-8444-444444444444"
PROJECT = "55555555-5555-4555-8555-555555555555"
MISSING = "66666666-6666-4666-8666-666666666666"
# Applied first, in this order: their filenames predate sortable timestamps.
EARLY = ["20260912_acs_plan_store_v2.sql", "20260912_acs_plan_store_v2_harden_functions.sql",
         "20260913_acs_plan_store_rpc_v2.sql", "20260913_acs_plan_store_rpc_v2_lockdown.sql"]
SETUP = """
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
count = 0


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def revision(rid, number, parent, marker):
    doc = {"revision_id": rid, "number": number, "parent_id": parent,
           "model_hash": marker * 64, "content_hash": "c" * 63 + marker,
           "bound_content_hash": "b" * 63 + marker, "created_at": "2026-11-25T00:00:00Z",
           "brief": "synthetic private text " + rid}
    return quote(json.dumps(doc, separators=(",", ":"))) + "::jsonb"


def approval(rid, marker):
    doc = {"revision_id": rid, "revision_content_hash": "c" * 63 + marker,
           "bound_content_hash": "b" * 63 + marker, "model_hash": marker * 64,
           "approved_at": "2026-11-25T00:00:00Z"}
    return quote(json.dumps(doc, separators=(",", ":"))) + "::jsonb"


def as_user(actor, sql, role="authenticated"):
    return "set role %s; select set_config('request.jwt.claim.sub',%s,false);\n%s\nreset role;\n" % (
        role, quote(actor), sql)


def expect(expr, label):
    global count
    count += 1
    return ("do $t$ begin if not coalesce((%s),false) then raise exception 'ASSERT: %s'; end if; "
            "raise notice 'PASS %s'; end $t$;" % (expr, label, label))


def denied(expr, label):
    global count
    count += 1
    return ("do $t$ declare refused boolean := false; begin begin perform %s; exception when others then "
            "if sqlstate not in ('P0001','42501') then raise; end if; refused := true; end; "
            "if not refused then raise exception 'SECURITY_REGRESSION: %s'; end if; "
            "raise notice 'PASS %s'; end $t$;" % (expr, label, label))


def bindir():
    configured = os.environ.get("PG_BINDIR")
    if configured:
        return Path(configured)
    for path in sorted(Path("/usr/lib/postgresql").glob("*/bin"), reverse=True):
        if (path / "postgres").is_file():
            return path
    print("NOT VERIFIED: PostgreSQL binaries unavailable; set PG_BINDIR")
    raise SystemExit(2)


def main():
    binary = bindir()
    with tempfile.TemporaryDirectory(prefix="acs-rpc-membership-") as temp:
        data = Path(temp) / "data"
        init = subprocess.run([str(binary / "initdb"), "-D", str(data), "--auth=trust",
                               "--no-locale", "--encoding=UTF8"], capture_output=True, text=True)
        if init.returncode:
            print("NOT VERIFIED: PostgreSQL initdb failed", init.stderr[-1000:])
            return 2

        def execute(sql, label):
            sql = "\n".join(line for line in sql.splitlines() if line.strip()) + "\n\n"
            done = subprocess.run([str(binary / "postgres"), "--single", "-j", "-c", "log_min_messages=notice", "-D", str(data), "postgres"],
                                  input=sql, capture_output=True, text=True)
            output = done.stdout + done.stderr
            if done.returncode or any(mark in output for mark in ("ERROR:", "FATAL:", "PANIC:")):
                print("FAIL", label)
                errors = [line for line in output.splitlines()
                          if any(mark in line for mark in ("ERROR:", "FATAL:", "PANIC:"))]
                print("\n".join(errors[:5]) or output[-3000:])
                return False
            for line in output.splitlines():
                if "NOTICE:  PASS" in line:
                    print("  PASS", line.split("NOTICE:  PASS ", 1)[1])
            return True

        if not execute(SETUP, "synthetic auth/storage setup"):
            return 1
        paths = list((ROOT / "supabase/migrations").glob("*.sql"))
        paths.sort(key=lambda p: (0, EARLY.index(p.name)) if p.name in EARLY else (1, p.name))
        for path in paths:
            if not execute(path.read_text(encoding="utf-8"), path.name):
                return 1
        fixtures = "insert into auth.users values %s;" % ",".join(
            "(%s)" % quote(x) for x in (OWNER, EDITOR, VIEWER, STRANGER))
        fixtures += "insert into public.acs_projects(id,owner_id,name) values (%s,%s,'Synthetic');" % (
            quote(PROJECT), quote(OWNER))
        fixtures += ("insert into public.acs_project_members(project_id,user_id,role) values "
                     "(%s,%s,'editor'),(%s,%s,'viewer');" % tuple(map(quote, (PROJECT, EDITOR, PROJECT, VIEWER))))
        if not execute(fixtures, "synthetic fixtures"):
            return 1
        p = quote(PROJECT)
        sql = as_user(OWNER, expect("(public.acs_save_plan_revision(%s,null,%s))->>'revision_id'='r1'"
                                    % (p, revision("r1", 1, None, "1")), "owner appends the first revision"))
        for who, label in ((STRANGER, "non-member"), (VIEWER, "viewer")):
            sql += as_user(who, denied("public.acs_save_plan_revision(%s,'r1',%s)"
                                       % (p, revision("x-" + label, 2, "r1", "9")), label + " cannot append a revision"))
            sql += as_user(who, denied("public.acs_plan_workspace_snapshot(%s)" % p,
                                       label + " cannot read full revision documents"))
            sql += as_user(who, denied("public.acs_save_plan_approval(%s,'r1',%s)" % (p, approval("r1", "1")),
                                       label + " cannot set the approved baseline"))
        sql += as_user(STRANGER, denied("public.acs_plan_project_state(%s)" % p, "non-member cannot read project state"))
        sql += as_user(STRANGER, denied("public.acs_plan_project_state(%s)" % quote(MISSING),
                                        "missing project is denied like an inaccessible one"))
        sql += as_user("", denied("public.acs_plan_project_state(%s)" % p, "anonymous caller denied"), role="anon")
        sql += as_user("", denied("public.acs_plan_workspace_snapshot(%s)" % p, "anonymous authenticated-role call denied"))
        sql += as_user(VIEWER, expect("(public.acs_plan_project_state(%s))->>'role'='viewer'" % p,
                                      "viewer still reads project metadata"))
        sql += as_user(EDITOR, expect("(public.acs_save_plan_revision(%s,'r1',%s))->>'revision_id'='r2'"
                                      % (p, revision("r2", 2, "r1", "2")), "editor still appends"))
        sql += as_user(OWNER, expect("(public.acs_save_plan_approval(%s,'r2',%s))->>'revision_id'='r2'"
                                     % (p, approval("r2", "2")), "owner still approves the head"))
        sql += as_user(OWNER, expect("jsonb_array_length((public.acs_plan_workspace_snapshot(%s))->'revisions')=2" % p,
                                     "owner still reads the full workspace"))
        sql += expect("(select array_agg(revision_id order by revision_number)=array['r1','r2'] "
                      "from public.acs_plan_revisions where project_id=%s)" % p,
                      "rejected calls left history unchanged")
        sql += expect("(select head_revision_id='r2' and baseline_revision_id='r2' from public.acs_projects where id=%s)" % p,
                      "head and baseline are exactly the writes of members")
        if not execute(sql, "plan RPC membership boundary"):
            return 1
        print("ACS plan RPC membership: PASS (%d assertions; real PostgreSQL, synthetic users)" % count)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
