-- ACS Design Pipeline v2 — close legacy direct-write bypasses after RPC rollout.
--
-- The base durable schema granted authenticated editors direct INSERT privileges
-- before the atomic PlanStorePort RPC boundary existed. Once revision/approval
-- writes move behind the row-locked RPCs, those legacy grants would let a client
-- bypass optimistic-head checks and Python canonical receipt validation, creating
-- orphan or malformed immutable rows. Keep SELECT for RLS-protected reads, but
-- require all canonical revision/approval writes to enter through the RPC layer.

revoke insert on table public.acs_plan_revisions from authenticated;
revoke insert on table public.acs_plan_approvals from authenticated;
