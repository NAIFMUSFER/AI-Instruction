# ACS pricing (approved by the owner, 2026-11-28)

Status: **approved, not yet charged**. No payment gateway is connected; the
site charges nothing until the billing work below ships.

## Price list (SAR, before 15% VAT)

| Package | Price | Includes |
|---|---|---|
| Brief reading and project program | free | the brief understood, the program and estimated areas; no full design |
| Residential project (villa or house) | 99 | full design, PDF plans, AutoCAD DXF, 3D model, Arabic report, 2 edits |
| Large project (apartment building, warehouse, clinics, offices, other) | 199 | the same outputs |
| Extra edit | 19 | one edit after the included ones |
| 5-project pack (contractors, real-estate marketers) | 399 | 5 projects (80 per project) |
| Office subscription | 999 / month | 12 projects a month |
| Launch offer | 49 | first project, for the first 500 users |

## Cost basis and guards

- Measured on the first ACS Designer pilot (Claude Managed Agents, 2026-11-28):
  a 4-storey, 12-flat building reached every drawing, the DXF and the 3D model
  for USD 3.69 at list price. Estimated cost per project including grading and
  two edits: SAR 20 to 45. Re-measure on the first 50 paid projects and report
  to the owner before margins go thin.
- Every designer session carries a hard spend cap (session budget):
  USD 8 (SAR 30) for a residential project, up to USD 10 (SAR 38) for a large one.
- The free tier never starts a full design (the costly part).
- Payment before generation; a failed generation returns the project credit.
- Payments on the website, not through app-store in-app purchase.
- Prices are reviewed every 3 months: model costs are in USD.

## Order of work

1. Owner tops up the Anthropic account; the five pilot sessions resume
   (`POST /admin/designer/sessions/{id}/resume`) and validate quality and cost
   on five building types.
2. The ACS Designer becomes the user-facing generation path.
3. Billing: credits ledger, gating of paid generation, and a Saudi payment
   gateway (merchant account opened by the owner).

Outputs are concept designs, not stamped permit drawings; the site says so.
Partnering with licensed offices to certify drawings is a later revenue line.
