#!/usr/bin/env python3
"""Deleting an uploaded plan source is limited to its uploader, on real PostgreSQL (U12).

Applies every migration in supabase/migrations, including
20261126120000_acs_plan_source_delete.sql, to an isolated socket-less cluster
with the same synthetic auth/storage stubs as test_plan_rpc_membership_postgres,
then deletes rows and storage objects as the uploader, another editor, a viewer
and a non-member. A shared original (two pages of one PDF) survives until the
last page that uses it is deleted. Missing PostgreSQL is a FAILURE, never a skip.
Never touches a configured database.

The single-user backend does not enforce row security, so each check evaluates
the migration's own DELETE policy predicate (read back from pg_policy) for the
row or object, as that caller, on real PostgreSQL.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import os

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_plan_rpc_membership_postgres as H  # noqa: E402

ROOT = H.ROOT
OWNER, EDITOR, OTHER, VIEWER, STRANGER = (
    "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222",
    "77777777-7777-4777-8777-777777777777", "33333333-3333-4333-8333-333333333333",
    "44444444-4444-4444-8444-444444444444")
PROJECT = "55555555-5555-4555-8555-555555555555"
PAGE1, PAGE2, OTHER_FILE = ("a1a1a1a1-0000-4000-8000-000000000001", "a1a1a1a1-0000-4000-8000-000000000002",
                            "b2b2b2b2-0000-4000-8000-000000000003")
SHA_A, SHA_B = "ab" * 32, "cd" * 32
CONTENT_A, CONTENT_B = str(uuid.UUID(hex=SHA_A[:32])), str(uuid.UUID(hex=SHA_B[:32]))
count = 0


POLICY = {"public.acs_plan_sources": "acs_plan_sources_delete_own",
          "storage.objects": "acs_plan_source_objects_delete_unreferenced"}


def deletes(table, where, expected, label):
    """The DELETE policy admits exactly ``expected`` rows; admitted rows are then
    deleted (as the cluster owner) so later checks see the new state."""
    global count
    count += 1
    return ("do $t$ declare qual text; n int; begin "
            "select pg_get_expr(polqual, polrelid) into strict qual from pg_policy "
            "where polname = '%s' and polcmd = 'd'; "
            "execute format('select count(*) from %s where (%%s) and (%s)', qual) into n; "
            "if n <> %d then raise exception 'SECURITY_REGRESSION: %s (%%)', n; end if; "
            "raise notice 'PASS %s'; end $t$;" % (POLICY[table], table, where.replace("'", "''"), expected,
                                                    label, label))





def obj(path):
    return "bucket_id='acs-plan-sources' and name=%s" % H.quote(PROJECT + "/" + path)


def main():
    binary = H.bindir()
    owner = H.cluster_owner()
    as_owner = ({} if owner is None else {"user": owner.pw_uid, "group": owner.pw_gid, "extra_groups": []})
    base = None if owner is None else ("/var/tmp" if os.path.isdir("/var/tmp") else "/tmp")
    with tempfile.TemporaryDirectory(prefix="acs-source-delete-", dir=base) as temp:
        if owner is not None:
            os.chown(temp, owner.pw_uid, owner.pw_gid)
        data = Path(temp) / "data"
        init = subprocess.run([str(binary / "initdb"), "-D", str(data), "--auth=trust", "--no-locale",
                               "--encoding=UTF8"], capture_output=True, text=True, cwd=temp, **as_owner)
        if init.returncode:
            H.fail("PostgreSQL initdb failed: %s" % init.stderr[-1000:].strip())

        def execute(sql, label):
            sql = "\n".join(line for line in sql.splitlines() if line.strip()) + "\n\n"
            done = subprocess.run([str(binary / "postgres"), "--single", "-j", "-c", "log_min_messages=notice",
                                   "-D", str(data), "postgres"], input=sql, capture_output=True, text=True,
                                  cwd=temp, **as_owner)
            output = done.stdout + done.stderr
            if done.returncode or any(mark in output for mark in ("ERROR:", "FATAL:", "PANIC:")):
                print("FAIL", label)
                print("\n".join(l for l in output.splitlines() if "ERROR:" in l or "FATAL:" in l)[:3000] or output[-3000:])
                return False
            for line in output.splitlines():
                if "NOTICE:  PASS" in line:
                    print("  PASS", line.split("NOTICE:  PASS ", 1)[1])
            return True

        # Supabase grants table privileges to `authenticated`; RLS decides.
        setup = H.SETUP + ("grant usage on schema storage to authenticated;"
                           "grant select, insert, delete on storage.objects to authenticated;")
        if not execute(setup, "synthetic auth/storage setup"):
            return 1
        paths = list((ROOT / "supabase/migrations").glob("*.sql"))
        paths.sort(key=lambda p: (0, H.EARLY.index(p.name)) if p.name in H.EARLY else (1, p.name))
        assert any(p.name == "20261126120000_acs_plan_source_delete.sql" for p in paths)
        for path in paths:
            if not execute(path.read_text(encoding="utf-8"), path.name):
                return 1
        q = H.quote
        fixtures = "insert into auth.users values %s;" % ",".join("(%s)" % q(x) for x in (OWNER, EDITOR, OTHER, VIEWER, STRANGER))
        fixtures += "insert into public.acs_projects(id,owner_id,name) values (%s,%s,'Synthetic');" % (q(PROJECT), q(OWNER))
        fixtures += ("insert into public.acs_project_members(project_id,user_id,role) values (%s,%s,'editor'),(%s,%s,'editor'),(%s,%s,'viewer');"
                     % (q(PROJECT), q(EDITOR), q(PROJECT), q(OTHER), q(PROJECT), q(VIEWER)))
        row = ("insert into public.acs_plan_sources(id,project_id,created_by,name,media_type,byte_size,sha256,page,page_count,"
               "preview_sha256,preview_media_type) values (%s,%s,%s,'plan.pdf','application/pdf',100,%s,%d,2,%s,'image/jpeg');")
        fixtures += row % (q(PAGE1), q(PROJECT), q(EDITOR), q(SHA_A), 1, q("e" * 64))
        fixtures += row % (q(PAGE2), q(PROJECT), q(EDITOR), q(SHA_A), 2, q("f" * 64))
        fixtures += row % (q(OTHER_FILE), q(PROJECT), q(OTHER), q(SHA_B), 1, q("9" * 64))
        for name in (PAGE1 + "/preview", PAGE2 + "/preview", OTHER_FILE + "/preview",
                     CONTENT_A + "/original", CONTENT_B + "/original"):
            fixtures += "insert into storage.objects(id,name,bucket_id) values (gen_random_uuid(),%s,'acs-plan-sources');" % q(PROJECT + "/" + name)
        if not execute(fixtures, "synthetic fixtures"):
            return 1
        sql = ""
        for who, label in ((STRANGER, "non-member"), (VIEWER, "viewer"), (OTHER, "another editor")):
            sql += H.as_user(who, deletes("public.acs_plan_sources", "id=%s" % q(PAGE1), 0, label + " cannot delete an uploaded page"))
        sql += H.as_user(EDITOR, deletes("storage.objects", obj(PAGE1 + "/preview"), 0, "a preview in use cannot be removed"))
        sql += H.as_user(EDITOR, deletes("public.acs_plan_sources", "id=%s" % q(PAGE1), 1, "the uploader deletes page 1"))
        sql += "delete from public.acs_plan_sources where id=%s;" % q(PAGE1)
        sql += H.as_user(VIEWER, deletes("storage.objects", obj(PAGE1 + "/preview"), 0, "a viewer cannot remove stored files"))
        sql += H.as_user(EDITOR, deletes("storage.objects", obj(PAGE1 + "/preview"), 1, "the orphaned page-1 preview is removed"))
        sql += "delete from storage.objects where %s;" % obj(PAGE1 + "/preview")
        sql += H.as_user(EDITOR, deletes("storage.objects", obj(CONTENT_A + "/original"), 0,
                                         "the shared original stays while page 2 still uses it"))
        sql += H.as_user(EDITOR, deletes("public.acs_plan_sources", "id=%s" % q(PAGE2), 1, "the uploader deletes page 2"))
        sql += "delete from public.acs_plan_sources where id=%s;" % q(PAGE2)
        sql += H.as_user(EDITOR, deletes("storage.objects", obj(CONTENT_A + "/original"), 1,
                                         "the shared original is removed with its last page"))
        sql += "delete from storage.objects where %s;" % obj(CONTENT_A + "/original")
        sql += H.as_user(EDITOR, deletes("storage.objects", obj(CONTENT_B + "/original"), 0,
                                         "an original another member still uses cannot be removed"))
        sql += H.expect("(select count(*)=1 from public.acs_plan_sources where project_id=%s)" % q(PROJECT),
                        "only the source of the other member remains")

        if not execute(sql, "plan source delete boundary"):
            return 1
        print("ACS plan source delete: PASS (%d assertions; real PostgreSQL, synthetic users)" % (count + H.count))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
