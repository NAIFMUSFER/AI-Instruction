# JANA Production Acceptance — 2026-09-09

## Status

Production preview is live on Render. This report records only checks actually executed against the isolated JANA Supabase project and Render service.

## PASS — Database invariants

- Negative stock balances: 0
- Negative / over-reserved inventory lots: 0
- Delivery slot capacity violations: 0
- Duplicate orders for the same quote: 0
- Financial violations (`refund > collected` or negative values): 0
- Completed orders not delivered: 0
- Delivered orders not completed: 0
- `jana_deep_health().ok`: true
- Active catalog items observed by deep health: 8
- Active delivery slots observed by deep health: 14

## PASS — RPC access boundary

After hardening all `public.jana_*` functions:

- JANA functions inspected: 54
- Executable by `anon`: 0
- Executable by `authenticated`: 0
- Missing `service_role` execute permission: 0

The Render backend remains the intended gateway and uses the service-role path. Direct PostgREST execution by client roles is blocked.

## PASS — Idempotency / concurrency guard

`orders.quote_id` already had a unique constraint (`orders_quote_id_key`). The redundant additional index created during hardening was removed. The existing unique constraint remains the database-level protection against converting one quote into multiple orders.

## Supabase advisor state

### Remaining informational findings

33 application tables have RLS enabled with no client policies. This is intentional in the current architecture because application access is routed through the backend service role rather than direct client table access.

### Remaining PostGIS-specific findings

These are not JANA RPC functions:

- `public.spatial_ref_sys` is reported without RLS.
- PostGIS is installed in the `public` schema.
- Supabase advisor continues to report the three PostGIS `st_estimatedextent(...)` overloads as executable by client roles.

Do not modify PostGIS ownership/schema mechanically in production without a dedicated PostGIS migration/compatibility test.

## Performance advisor

The duplicate-index warning is cleared. Remaining findings are `unused_index` INFO notices. No indexes were bulk-dropped because the service is new/low-traffic and lack of usage statistics is not evidence that an index is unnecessary.

## External integrations not certified

- Google Maps JavaScript API key is not configured. Browser high-accuracy geolocation and Google Maps link/preview fallback remain available.
- SMS / Push / object storage / online payment providers are outside the current critical path and were intentionally not claimed as production-certified.

## Live surfaces

- Storefront: https://jana-live.onrender.com
- Operations: https://jana-live.onrender.com/ops
- Administration: https://jana-live.onrender.com/admin

## Acceptance classification

- Core data invariants: PASS
- JANA direct-RPC exposure: PASS
- Quote-to-order duplicate guard: PASS
- Render deployment: LIVE
- PostGIS advisor cleanup: OPEN / isolated to extension-owned objects
- Google Maps SDK: NOT VERIFIED (API key absent)
- Full external-provider acceptance: NOT RUN
