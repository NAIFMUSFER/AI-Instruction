# Scope and limits — 4.1.0

## Geometry and architecture

The design is conceptual. Rectangular site generation accepts widths 12–120 m,
depths 15–160 m, 1–8 floors and 1–16 bedrooms for residential programs. Generated
setbacks, slab thicknesses, wall layers and opening types are conceptual assumptions,
not local authority rules or validated construction specifications. Areas follow
canonical space boundaries; they are not certified finished clear areas.

Rooms can carry a simple orthogonal polygon with up to 24 vertices. The current
interactive shape tool creates a single corner notch from a rectangle. General
vertex drawing/editing, curved walls, arbitrary rotations, sloped roofs and curved
surfaces are not provided. Unsupported resize/swap on a polygon is rejected.
Stairs/elevators/pools are conceptual space/site placeholders, not engineered systems.
The default slab and roof are rectangular envelopes, not detailed openings/slopes.

Walls are derived from boundaries and assigned stable IDs for unchanged geometry.
Moving/splitting a wall changes its geometric identity. Do not describe these as
persistent authoring IDs across arbitrary topology changes. A door/window must fit
one atomized host segment; an aperture crossing a T-junction is rejected. The
model does not provide arbitrary independent wall or multi-discipline authoring.

## IFC

The exporter emits IFC4 architectural subset elements: spaces, walls/material layers,
floor/roof slabs, door/window fillings and hosted opening voids. Site containers are
not survey/georeferencing evidence. Stairs, pool equipment and MEP are not exported
as independently engineered IFC elements. Independent EXPRESS and geometry tests
are provided, but no Revit/Archicad/Tekla certification or MVD claim is made.

The importer accepts supported IFC4 SI units, axis-aligned local translations,
vertical extrusions and orthogonal closed profiles, and tagged MASAR openings.
It rejects unsupported rotations, tilted geometry, ambiguous bodies, bad references,
cycles, truncated files and unsupported schemas. Imported wall layers, unsupported
objects, requirements and history are not reconstructed; the review explicitly
states defaults/omissions. MASAR JSON is the lossless project/history format.

## Assessment and AI

Internal movement/privacy/outdoor/efficiency indicators are declared comparison
heuristics. A 'checked' result only names a implemented conceptual check. Structural,
MEP, fire, accessibility and regulatory disciplines remain unchecked. Imported
metadata cannot promote these disciplines to approved. The software cannot issue
construction permission or certify life safety.

Local language understanding is deterministic and bounded. Optional Anthropic
proposals require operator credentials/model configuration and user consent; they
cannot commit automatically. No live paid provider request is part of the default
test suite. PDF/images are not automatically converted into trustworthy BIM.

## Operations

SQLite runs in one application instance. A host's ephemeral disk can lose accounts,
projects and shares on recreation. The 'persistent' classification is operator
configuration, not automatic proof of a correctly provisioned cloud disk. A local
Docker volume test proves only the tested volume lifecycle. Production requires
HTTPS, managed durable volume/backups, monitoring and recovery drills.

Public signup, password mail recovery, email verification, organization/team roles,
SSO, payments and live collaborative multi-writer editing are not implemented as
production SaaS services. Sessions expire after seven days. Local browser data is
not deleted at logout. Anyone holding an unrevoked review link can access it.
The server uses conservative direct-peer rate limits and does not trust arbitrary
forwarding headers; shared reverse-proxy clients can share an IP bucket.

Project histories are bounded at 100 revisions and fail explicitly at the bound.
Export before creating an independent continuation project. File/reference sizes
and request sizes are bounded; uploaded unsupported formats fail explicitly.
