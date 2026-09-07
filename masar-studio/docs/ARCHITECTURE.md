# MASAR Studio 4 — Architecture

## 1. حدود مصدر الحقيقة

### Canonical model — `shared/model.js`
مصدر الحقيقة للهندسة القابلة للتحرير: site، levels، rooms/spaces، doors، windows، optional orthogonal `footprint`، requirements، locks، comments، design settings وauthoring configuration. `schemaVersion` بقي 1 للتوافق؛ حقول 4.0 اختيارية ولها defaults آمنة.

### Authoring definitions — `shared/authoring.js`
يعرف wall/window types الافتراضية ويحسب النوع الفعلي. هذه **بيانات تأليف/تنسيق** وليست specification إنشائية/حرارية/حريقية.

### Revision history
Append-only. Undo/Redo/Restore لا تمحو الماضي؛ تنتج حالة أمامية قابلة للتتبع.

### Derived building layer — `shared/building.js`
اشتقاق حتمي من canonical model:

- atomized walls من حدود المساحات المتعامدة.
- wall type/thickness/layers.
- hosted doors/windows.
- spaces, slabs, conceptual roof, site features.
- schedules, traceability, product-quality rules, IFC export.

لا توجد قناة كتابة من derived wall/slab/IFC entity إلى canonical object.

### IFC import boundary — `shared/ifc.js`
هذا ليس reverse-write للـderived graph. parser مستقل ومحدود يحول **subset IFC4 معروفًا** إلى مشروع MASAR canonical جديد بعد تأكيد المستخدم. unsupported geometry ترفض صراحة.

## 2. Data flow

```text
Prompt / MASAR JSON / DXF reference / image reference / supported IFC4
        ↓
explicit parse + user confirmation
        ↓
Canonical MASAR Model
        ├─> SVG plan / measurement
        ├─> 3D presentation geometry
        ├─> Derived Building Graph
        │      ├─ composite walls
        │      ├─ hosted openings
        │      ├─ slabs/roof/site
        │      ├─ schedules + quality
        │      └─ IFC4 export
        └─> reports / exports / immutable review snapshots

Edit / Arabic command
        ↓
Candidate clone
        ↓
Lock + canonical integrity + host/overlap checks
        ↓
Impact + issue diff
        ↓
Preview ── cancel
        ↓ explicit commit
New Revision
```

## 3. Geometry model

### Rectangular space
`x,y,w,d,height` define the footprint.

### Orthogonal authored space
`footprint` contains 4–24 finite points forming a simple, axis-aligned closed boundary. `x/y/w/d` remain the **bounding box** and validation requires exact bbox agreement. This allows existing selection/layout infrastructure to remain compatible while area/walls/2D/3D/DXF/IFC use the exact polygon.

No diagonal, arc or spline edge is accepted in 4.0.

## 4. Hosted openings

Canonical door/window carries stable identity and room-side placement. `deriveOpenings()` resolves a derived host wall. Quality/validation surfaces missing host rather than inventing one.

Presentation wall boxes are split around openings:

- door: cut from floor to door height.
- window: cut from sill to sill + height.

IFC export represents hosted openings through `IfcOpeningElement` + void/fill relationships.

## 5. Composite walls

Wall types contain named layers and total thickness. Validation/quality checks require layer thickness sum to match total thickness. Derived wall picks external/internal type based on room-boundary adjacency.

Changing wall layers is a project edit: UI creates a preview; only explicit commit records it in history.

## 6. Identity

- rooms/doors/windows: canonical stored IDs.
- derived walls: deterministic level + geometric segment IDs; stable while segment geometry is unchanged.
- hosted opening derived record retains canonical opening ID.
- IFC GUIDs: deterministic compressed IDs from source identity for one export model.

## 7. Validation boundary

`validate()` checks **MASAR model integrity**: finite/positive geometry, site bounds, overlap, orthogonal polygon validity, opening fit/boundary conditions, locked-data consistency and declared model connectivity checks.

`evaluateRulePack()` is versioned product QA: `masar-authoring-quality-2026.2`, `authority=product-heuristic`, `compliance=false`.

Structural adequacy, MEP, fire, accessibility and regulatory compliance remain `unchecked`.

## 8. Presentation state is not model state

Not revisioned: camera, selected room, measurement points, display mode, cutaway, furniture visibility.

Revisioned: geometry/footprint, doors/windows, authoring types, locks, requirements, design settings and internal comments.

External share review comments live server-side outside the snapshot document.

## 9. Storage/server

Browser storage uses IndexedDB when available. Server uses Node HTTP + built-in SQLite for users, hashed sessions, projects, immutable share snapshots and review comments. Project saves use integer optimistic compare-and-swap.

## 10. Build/PWA

`tools/build.mjs` bundles Authoring → Model → Building → IFC → Geometry → Renderer/Storage/App into one standalone `dist/index.html` with exact CSP script hash and no external runtime dependency.

The PWA service worker caches only the public shell and shared browser modules, including `authoring.js` and `ifc.js`; it is not cloud backup.
