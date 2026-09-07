# MASAR Studio 4 — API

Base path: `/api`. JSON writes تحتاج `Origin` مطابقًا لـ`PUBLIC_ORIGIN`. Authenticated writes تحتاج session + CSRF. Authoring/IFC parsing نفسه يحدث في shared client modules؛ لم يُضف endpoint خفي يتجاوز model validation.

## Health

- `GET /api/health` → `{ok, version, schemaVersion, storage, aiConfigured, registration}`؛ version = `4.1.0`.

## Auth

- `GET /api/auth/me`
- `POST /api/auth/register` — إذا `ALLOW_REGISTRATION=true`.
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `POST /api/auth/change-password`
- `DELETE /api/auth/account` — يتطلب كلمة المرور الحالية.

Passwords 12–200 حرف. التخزين scrypt salt+hash؛ لا plain text.

## Projects

- `GET /api/projects`
- `GET /api/projects/:id`
- `PUT /api/projects/:id` — `{history, version}` مع optimistic compare-and-swap؛ stale → `409`.
- `DELETE /api/projects/:id`

`assertHistory` وcanonical validation يعملان قبل persistence؛ projects القديمة schema v1 تبقى متوافقة وauthoring defaults اختيارية.

## Shares

- `GET /api/shares`
- `POST /api/shares` — `{model, days}` و`days ∈ {1,7,30}`، owner-only.
- `GET /api/shares/:token` — immutable active snapshot.
- `DELETE /api/shares/:shareId` — owner-only revoke.

## Review comments

Public active share:

- `GET /api/shares/:token/comments`
- `POST /api/shares/:token/comments` — `{author,text,targetId}`؛ target يجب أن يوجد في snapshot.

Owner:

- `GET /api/projects/:id/review-comments`
- `POST /api/review-comments/:commentId` — `{resolved}`.

Review comments لا تغير snapshot/model/revision.

## Optional AI

- `POST /api/ai/propose`

عند ضبط `ANTHROPIC_API_KEY` و`ANTHROPIC_MODEL` فقط. العقد يسمح command proposal لأنواع محددة، بما فيها `window` و`notch`، ولا يمنح AI صلاحية commit. UI يعيد parser/locks/preview/validation قبل أي اعتماد.

## Errors

- `400` invalid JSON/input/content-type.
- `401` authentication.
- `403` Origin/CSRF/ownership.
- `404` missing resource.
- `409` stale/concurrency conflict.
- `422` schema/semantic validation.
- `429` rate limit.
- `503` optional AI unavailable/unconfigured.
