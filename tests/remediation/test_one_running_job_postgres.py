#!/usr/bin/env python3
"""Audit P0-3 on real PostgreSQL: one RUNNING job per project, for every server.

Applies every migration in supabase/migrations to an isolated, socket-less
cluster (the harness of test_plan_rpc_membership_postgres), then writes jobs
as synthetic members, the way two server instances would for one project:
the second RUNNING row is refused whoever writes it, other projects are not
affected, a finished job frees the project, and acs_release_stale_job frees
only a job no worker can still finish (35 minutes for a workspace job, 3 hours
for an ACS Designer job), only for an owner or editor. Never touches a
configured database. Missing PostgreSQL is a FAILURE, never a skip.

    PG_BINDIR=/usr/lib/postgresql/16/bin python tests/remediation/test_one_running_job_postgres.py
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import test_plan_rpc_membership_postgres as M  # noqa: E402

OWNER, EDITOR, VIEWER, STRANGER = M.OWNER, M.EDITOR, M.VIEWER, M.STRANGER
PROJECT, OTHER = M.PROJECT, "77777777-7777-4777-8777-777777777777"
JOBS = ["aaaaaaaa-aaaa-4aaa-8aaa-%012d" % n for n in range(1, 9)]
WORKER_A, WORKER_B = "0000000a-0000-4000-8000-00000000000a", "0000000b-0000-4000-8000-00000000000b"


def insert(job, project, actor, worker, kind=None):
    checkpoint = "'{\"kind\":\"%s\"}'::jsonb" % kind if kind else "null"
    return ("insert into public.acs_workspace_jobs(id,project_id,created_by,input_hash,worker_id,state,checkpoint) "
            "values (%s,%s,%s,repeat('a',64),%s,'RUNNING',%s);"
            % (M.quote(job), M.quote(project), M.quote(actor), M.quote(worker), checkpoint))


def refused(sql, label):
    """Only the one-running-job index may refuse it; any other error fails."""
    M.count += 1
    return ("do $t$ declare refused boolean := false; begin begin %s exception when unique_violation then "
            "if sqlerrm not like '%%acs_workspace_jobs_one_running%%' then raise; end if; refused := true; end; "
            "if not refused then raise exception 'P0-3 REGRESSION: %s'; end if; "
            "raise notice 'PASS %s'; end $t$;" % (sql, label, label))


def age(job, interval):
    return "update public.acs_workspace_jobs set created_at = now() - interval %s where id = %s;" % (
        M.quote(interval), M.quote(job))


def main():
    binary = M.bindir()
    owner = M.cluster_owner()
    as_owner = ({} if owner is None else {"user": owner.pw_uid, "group": owner.pw_gid, "extra_groups": []})
    base = None if owner is None else ("/var/tmp" if os.path.isdir("/var/tmp") else "/tmp")
    with tempfile.TemporaryDirectory(prefix="acs-one-running-", dir=base) as temp:
        if owner is not None:
            os.chown(temp, owner.pw_uid, owner.pw_gid)
        data = Path(temp) / "data"
        init = subprocess.run([str(binary / "initdb"), "-D", str(data), "--auth=trust", "--no-locale",
                               "--encoding=UTF8"], capture_output=True, text=True, cwd=temp, **as_owner)
        if init.returncode:
            M.fail("PostgreSQL initdb failed: %s" % init.stderr[-1000:].strip())

        def execute(sql, label):
            sql = "\n".join(line for line in sql.splitlines() if line.strip()) + "\n\n"
            done = subprocess.run([str(binary / "postgres"), "--single", "-j", "-c", "log_min_messages=notice",
                                   "-D", str(data), "postgres"], input=sql, capture_output=True, text=True,
                                  cwd=temp, **as_owner)
            output = done.stdout + done.stderr
            if done.returncode or any(mark in output for mark in ("ERROR:", "FATAL:", "PANIC:")):
                print("FAIL", label)
                errors = [line for line in output.splitlines() if any(m in line for m in ("ERROR:", "FATAL:", "PANIC:"))]
                print("\n".join(errors[:5]) or output[-3000:])
                return False
            for line in output.splitlines():
                if "NOTICE:  PASS" in line:
                    print("  PASS", line.split("NOTICE:  PASS ", 1)[1])
            return True

        if not execute(M.SETUP, "synthetic auth/storage setup"):
            return 1
        paths = list((M.ROOT / "supabase/migrations").glob("*.sql"))
        paths.sort(key=lambda p: (0, M.EARLY.index(p.name)) if p.name in M.EARLY else (1, p.name))
        for path in paths:
            if not execute(path.read_text(encoding="utf-8"), path.name):
                return 1
        q = M.quote
        fixtures = "insert into auth.users values %s;" % ",".join("(%s)" % q(x) for x in (OWNER, EDITOR, VIEWER, STRANGER))
        for project in (PROJECT, OTHER):
            fixtures += "insert into public.acs_projects(id,owner_id,name) values (%s,%s,'Synthetic');" % (q(project), q(OWNER))
            fixtures += ("insert into public.acs_project_members(project_id,user_id,role) values (%s,%s,'editor'),(%s,%s,'viewer');"
                         % (q(project), q(EDITOR), q(project), q(VIEWER)))
        if not execute(fixtures, "synthetic fixtures"):
            return 1
        a, b, c, d, e, f, g, h = JOBS
        p = q(PROJECT)
        running = "(select count(*) from public.acs_workspace_jobs where project_id=%s and state='RUNNING')" % p
        sql = M.as_user(EDITOR, insert(a, PROJECT, EDITOR, WORKER_A))
        sql += M.expect(running + "=1", "server A starts a job for the project")
        sql += M.as_user(EDITOR, refused(insert(b, PROJECT, EDITOR, WORKER_B), "server B cannot start a second job for it"))
        sql += M.as_user(OWNER, refused(insert(c, PROJECT, OWNER, WORKER_B), "nor can another member of the project"))
        sql += M.as_user(EDITOR, insert(d, OTHER, EDITOR, WORKER_B))
        sql += M.expect("exists (select 1 from public.acs_workspace_jobs where id=%s and state='RUNNING')" % q(d),
                        "another project runs at the same time")
        # A live job is not released, whoever asks.
        sql += M.as_user(OWNER, M.expect("public.acs_release_stale_job(%s)=0" % p, "a job a worker may still finish stays"))
        for who, label in ((VIEWER, "viewer"), (STRANGER, "non-member")):
            sql += M.as_user(who, M.denied("public.acs_release_stale_job(%s)" % p, label + " cannot release the job of the project"))
        sql += M.as_user("", M.denied("public.acs_release_stale_job(%s)" % p, "anonymous caller cannot release"), role="anon")
        # A job past every worker deadline is released for the next one.
        sql += age(a, "36 minutes")
        sql += M.as_user(OWNER, M.expect("public.acs_release_stale_job(%s)=1" % p, "a job past every deadline is released"))
        sql += M.expect("(select state='FAILED' and error_code='PROVIDER_OUTCOME_UNKNOWN' and finished_at is not null "
                        "from public.acs_workspace_jobs where id=%s)" % q(a), "it is failed with an unknown provider outcome")
        sql += M.as_user(OWNER, insert(e, PROJECT, OWNER, WORKER_B))
        sql += M.expect(running + "=1", "the next job starts once the dead one is released")
        # A finished job frees the project; the creator still updates it under RLS.
        sql += M.as_user(OWNER, "update public.acs_workspace_jobs set state='SUCCEEDED', finished_at=now() where id=%s;" % q(e))
        sql += M.as_user(EDITOR, insert(f, PROJECT, EDITOR, WORKER_A, kind="designer"))
        sql += M.expect(running + "=1", "a design starts once the last job finished")
        # A design runs in its Managed Agents session: 40 minutes is not stale, 4 hours is.
        sql += age(f, "40 minutes")
        sql += M.as_user(EDITOR, M.expect("public.acs_release_stale_job(%s)=0" % p, "a 40-minute design is still running"))
        sql += M.as_user(OWNER, refused(insert(g, PROJECT, OWNER, WORKER_B), "and still holds the project"))
        sql += age(f, "4 hours")
        sql += M.as_user(EDITOR, M.expect("public.acs_release_stale_job(%s)=1" % p, "a design past 3 hours is released"))
        sql += M.as_user(OWNER, insert(h, PROJECT, OWNER, WORKER_B))
        sql += M.expect(running + "=1 and (select count(*) from public.acs_workspace_jobs where project_id=%s)=4" % p,
                        "exactly one job runs and no refused write left a row")
        if not execute(sql, "one running job per project"):
            return 1
        print("ACS one running job per project: PASS (%d assertions; real PostgreSQL, synthetic users)" % M.count)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
