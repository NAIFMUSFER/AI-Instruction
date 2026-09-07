import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createApp } from '../server/server.mjs';
import { createHistory, generate, understand, clone } from '../shared/model.js';
const origin = 'http://masar.test';
const fixture = () => createHistory(generate(understand('أرض 20×25 ثلاثة أدوار خمس غرف نوم')));
async function start(dbPath = ':memory:', extra = {}) {
    const app = await createApp({ dbPath, origin, port: 0, ...extra });
    await new Promise(resolve => app.server.listen(0, '127.0.0.1', resolve));
    const base = 'http://127.0.0.1:' + app.server.address().port;
    async function req(url, { method = 'GET', body, cookie, csrf, requestOrigin = origin, contentType = 'application/json' } = {}) { const headers = {}; if (method !== 'GET') {
        if (requestOrigin !== null)
            headers.Origin = requestOrigin;
        if (contentType)
            headers['Content-Type'] = contentType;
    } if (cookie)
        headers.Cookie = cookie; if (csrf)
        headers['X-CSRF-Token'] = csrf; const res = await fetch(base + url, { method, headers, body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body) }); let value; const text = await res.text(); try {
        value = JSON.parse(text);
    }
    catch {
        value = text;
    } return { status: res.status, headers: res.headers, body: value }; }
    async function user(email = 'one@example.test') { const r = await req('/api/auth/register', { method: 'POST', body: { email, name: 'مستخدم تجريبي', password: 'Correct-pass-12345' } }); assert.equal(r.status, 201); return { cookie: r.headers.get('set-cookie').split(';')[0], csrf: r.body.csrf, id: r.body.user.id }; }
    return { ...app, req, user, close: () => new Promise(resolve => app.server.close(resolve)) };
}
test('HTTP authentication, isolated projects, optimistic concurrency, and sharing', async (t) => {
    const app = await start();
    t.after(app.close);
    const { req, user, db } = app;
    const h = fixture();
    let a, b, shareToken, shareId;
    await t.test('Health endpoint reports configured capabilities without secrets', async () => { const r = await req('/api/health'); assert.equal(r.status, 200); assert.equal(r.body.aiConfigured, false); assert.equal(r.body.version,'4.1.0'); assert.ok(!JSON.stringify(r.body).includes('API_KEY')); });
    await t.test('Unauthenticated project access is denied', async () => { assert.equal((await req('/api/projects')).status, 401); });
    await t.test('Cross-origin registration is denied before account creation', async () => { const r = await req('/api/auth/register', { method: 'POST', requestOrigin: 'https://evil.test', body: {} }); assert.equal(r.status, 403); assert.equal(db.prepare('SELECT count(*) AS n FROM users').get().n, 0); });
    await t.test('Missing Origin is denied on a write', async () => { assert.equal((await req('/api/auth/register', { method: 'POST', requestOrigin: null, body: {} })).status, 403); });
    await t.test('Creates two real accounts with secure server sessions', async () => { a = await user(); b = await user('two@example.test'); const row = db.prepare('SELECT password FROM users WHERE id=?').get(a.id); assert.ok(!row.password.includes('Correct-pass')); assert.match(row.password, /^[a-f0-9]{32}:[a-f0-9]{128}$/); const session = db.prepare('SELECT token_hash FROM sessions WHERE user_id=?').get(a.id); assert.ok(!a.cookie.includes(session.token_hash)); });
    await t.test('Login cookie is HTTP-only, strict SameSite, and password never returned', async () => { const r = await req('/api/auth/login', { method: 'POST', body: { email: 'one@example.test', password: 'Correct-pass-12345' } }); assert.equal(r.status, 200); assert.match(r.headers.get('set-cookie'), /HttpOnly/); assert.match(r.headers.get('set-cookie'), /SameSite=Strict/); assert.ok(!JSON.stringify(r.body).includes('password')); });
    await t.test('Wrong password is rejected', async () => { assert.equal((await req('/api/auth/login', { method: 'POST', body: { email: 'one@example.test', password: 'wrong-pass' } })).status, 401); });
    await t.test('CSRF token required for authenticated writes', async () => { assert.equal((await req('/api/projects/' + h.projectId, { method: 'PUT', cookie: a.cookie, body: { history: h, version: 0 } })).status, 403); });
    await t.test('Valid save round-trips the complete history', async () => { const r = await req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: { history: h, version: 0 } }); assert.equal(r.status, 200); assert.equal(r.body.version, 1); const read = await req('/api/projects/' + h.projectId, a); assert.deepEqual(read.body.history, h); });
    await t.test('Another account cannot read or delete an owner project', async () => { assert.equal((await req('/api/projects/' + h.projectId, b)).status, 404); assert.equal((await req('/api/projects/' + h.projectId, { method: 'DELETE', ...b, body: {} })).status, 404); assert.equal((await req('/api/projects', b)).body.projects.length, 0); });
    await t.test('Stale project version cannot overwrite a newer save', async () => { assert.equal((await req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: { history: h, version: 0 } })).status, 409); const changed = clone(h); changed.revisions[0].model.title = 'نسخة محدثة'; assert.equal((await req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: { history: changed, version: 1 } })).body.version, 2); });
    await t.test('Invalid schema cannot be stored', async () => { const malformed = clone(h); malformed.revisions[0].model.levels[0].rooms[0].w = -2; assert.equal((await req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: { history: malformed, version: 2 } })).status, 422); });
    await t.test('Malformed JSON and wrong content type fail explicitly', async () => { assert.equal((await req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: '{broken' })).status, 400); assert.equal((await req('/api/projects/' + h.projectId, { method: 'PUT', ...a, contentType: 'text/plain', body: '{}' })).status, 415); });
    await t.test('Share creation requires project ownership', async () => { assert.equal((await req('/api/shares', { method: 'POST', ...b, body: { model: h.revisions[0].model } })).status, 404); });
    await t.test('A share is an immutable snapshot with a seven-day expiry', async () => { const snapshot = clone(h.revisions[0].model); snapshot.comments = []; snapshot.brief.prompt = 'redacted'; const r = await req('/api/shares', { method: 'POST', ...a, body: { model: snapshot } }); assert.equal(r.status, 201); shareToken = new URL(r.body.url).searchParams.get('share'); shareId = r.body.id; assert.ok(r.body.expires > Date.now() + 6 * 86400000); const shared = await req('/api/shares/' + shareToken); assert.equal(shared.status, 200); assert.equal(shared.body.readOnly, true); assert.equal(shared.body.model.brief.prompt, 'redacted'); assert.ok(!Object.hasOwn(shared.body, 'history')); });
    await t.test('Review-link comments are scoped to the shared snapshot and never mutate it', async () => {
        const targetId=h.revisions[0].model.levels[0].rooms[0].id;
        assert.equal((await req('/api/shares/'+shareToken+'/comments',{method:'POST',body:{author:'مراجع',text:'باب المجلس يحتاج مراجعة',targetId:'not-a-room'}})).status,422);
        const posted=await req('/api/shares/'+shareToken+'/comments',{method:'POST',body:{author:'مراجع خارجي',text:'راجع خصوصية مدخل المجلس',targetId}});
        assert.equal(posted.status,201); assert.equal(posted.body.comment.targetId,targetId);
        const comments=await req('/api/shares/'+shareToken+'/comments'); assert.equal(comments.status,200); assert.equal(comments.body.comments.length,1); assert.equal(comments.body.comments[0].text,'راجع خصوصية مدخل المجلس');
        const shared=await req('/api/shares/'+shareToken); assert.equal(shared.body.model.comments.length,0,'review comments must not mutate immutable share model');
        const owner=await req('/api/projects/'+h.projectId+'/review-comments',a); assert.equal(owner.status,200); assert.equal(owner.body.comments.length,1);
        assert.equal((await req('/api/projects/'+h.projectId+'/review-comments',b)).status,404);
        const cid=owner.body.comments[0].id; assert.equal((await req('/api/review-comments/'+cid,{method:'POST',...b,body:{resolved:true}})).status,404);
        assert.equal((await req('/api/review-comments/'+cid,{method:'POST',...a,body:{resolved:true}})).status,200);
        assert.equal((await req('/api/shares/'+shareToken+'/comments')).body.comments[0].resolved,true);
    });
    await t.test('Another account cannot revoke an owner share', async () => { assert.equal((await req('/api/shares/' + shareId, { method: 'DELETE', ...b, body: {} })).status, 404); });
    await t.test('Share expiry is caller-selected only from 1, 7 or 30 days', async () => { const one = await req('/api/shares', { method: 'POST', ...a, body: { model: h.revisions[0].model, days: 1 } }); assert.equal(one.status, 201); assert.ok(one.body.expires > Date.now() + 23 * 3600000 && one.body.expires < Date.now() + 25 * 3600000); const thirty = await req('/api/shares', { method: 'POST', ...a, body: { model: h.revisions[0].model, days: 30 } }); assert.equal(thirty.status, 201); assert.ok(thirty.body.expires > Date.now() + 29 * 86400000); assert.equal((await req('/api/shares', { method: 'POST', ...a, body: { model: h.revisions[0].model, days: 2 } })).status, 400); });
    await t.test('Owner can revoke a share immediately and review comments cascade', async () => { assert.equal((await req('/api/shares/' + shareId, { method: 'DELETE', ...a, body: {} })).status, 200); assert.equal((await req('/api/shares/' + shareToken)).status, 404); assert.equal(db.prepare('SELECT count(*) n FROM share_comments WHERE share_id=?').get(shareId).n,0); });
    await t.test('Expired links cannot retrieve the document', async () => { const r = await req('/api/shares', { method: 'POST', ...a, body: { model: h.revisions[0].model } }); const token = new URL(r.body.url).searchParams.get('share'); db.prepare('UPDATE shares SET expires=0 WHERE id=?').run(r.body.id); assert.equal((await req('/api/shares/' + token)).status, 404); });
    await t.test('No AI key means honest service-unavailable, not a fake success', async () => { assert.equal((await req('/api/ai/propose', { method: 'POST', ...a, body: {} })).status, 503); });
    await t.test('Private files, secrets and source-server files are not served', async () => { for (const p of ['/data/masar.sqlite', '/.env', '/server/server.mjs', '/package.json', '/public/../../etc/passwd'])
        assert.equal((await req(p)).status, 404); });
    await t.test('Served app has CSP, no framing and no MIME sniffing', async () => { const r = await req('/'); assert.equal(r.status, 200); assert.match(r.headers.get('content-security-policy'), /script-src 'self'/); assert.equal(r.headers.get('x-frame-options'), 'DENY'); assert.equal(r.headers.get('x-content-type-options'), 'nosniff'); assert.match(r.body, /src="\/src\/app.js"/); });
    await t.test('PWA manifest and service worker are served but private JS remains blocked', async () => { assert.equal((await req('/public/manifest.webmanifest')).status, 200); const sw=await req('/public/sw.js'); assert.equal(sw.status,200); assert.match(sw.body,/masar-4\.1\.0-shell/); assert.equal((await req('/server/server.mjs')).status,404); });
    await t.test('Password change verifies current password, strengthens new password, and preserves current session only', async () => { assert.equal((await req('/api/auth/change-password',{method:'POST',...b,body:{currentPassword:'wrong',newPassword:'Another-strong-pass-987'}})).status,401); assert.equal((await req('/api/auth/change-password',{method:'POST',...b,body:{currentPassword:'Correct-pass-12345',newPassword:'Another-strong-pass-987'}})).status,200); assert.equal((await req('/api/auth/login',{method:'POST',body:{email:'two@example.test',password:'Correct-pass-12345'}})).status,401); assert.equal((await req('/api/auth/login',{method:'POST',body:{email:'two@example.test',password:'Another-strong-pass-987'}})).status,200); assert.equal((await req('/api/projects',b)).status,200); });
    await t.test('Account deletion requires password and cascades server-side identity data', async () => { assert.equal((await req('/api/auth/account',{method:'DELETE',...b,body:{password:'wrong'}})).status,401); assert.equal((await req('/api/auth/account',{method:'DELETE',...b,body:{password:'Another-strong-pass-987'}})).status,200); assert.equal((await req('/api/projects',b)).status,401); assert.equal(db.prepare('SELECT count(*) n FROM users WHERE id=?').get(b.id).n,0); });
    await t.test('Logging out invalidates the session in the database', async () => { assert.equal((await req('/api/auth/logout', { method: 'POST', ...a, body: {} })).status, 200); assert.equal((await req('/api/projects', a)).status, 401); });
});
test('Rate limit is enforced without trusting user supplied forwarding headers', async (t) => { const app = await start(); t.after(app.close); for (let i = 0; i < 10; i++)
    assert.equal((await app.req('/api/auth/register', { method: 'POST', body: {} })).status, 400); assert.equal((await app.req('/api/auth/register', { method: 'POST', body: {} })).status, 429); });
test('Production cannot start with an implicit or non-HTTPS origin', async () => { await assert.rejects(() => createApp({ production: true, origin: 'http://not-secure.test', dbPath: ':memory:' }), /HTTPS/); });
test('SQLite persistence survives a complete server restart', async () => { const dir = await mkdtemp(path.join(os.tmpdir(), 'masar-test-')); const dbPath = path.join(dir, 'test.sqlite'), h = fixture(); let app; try {
    app = await start(dbPath);
    const a = await app.user();
    assert.equal((await app.req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: { history: h, version: 0 } })).status, 200);
    await app.close();
    app = await start(dbPath);
    const result = await app.req('/api/projects/' + h.projectId, a);
    assert.equal(result.status, 200);
    assert.deepEqual(result.body.history, h);
    await app.close();
    app = null;
}
finally {
    if (app)
        await app.close();
    await rm(dir, { recursive: true, force: true });
} });
test('Overlapping streamed saves cannot both overwrite the same version', async (t) => {
    const app = await start();
    t.after(app.close);
    const a = await app.user(), h = fixture();
    await app.req('/api/projects/' + h.projectId, { method: 'PUT', ...a, body: { history: h, version: 0 } });
    const { request } = await import('node:http');
    const payload = JSON.stringify({ history: h, version: 1 });
    const streams = [];
    const pending = [0, 1].map(() => new Promise((resolve, reject) => {
        const req = request({ host: '127.0.0.1', port: app.server.address().port, path: '/api/projects/' + h.projectId, method: 'PUT', headers: { Origin: origin, Cookie: a.cookie, 'X-CSRF-Token': a.csrf, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) } }, res => { res.resume(); res.on('end', () => resolve(res.statusCode)); });
        req.on('error', reject);
        req.write(payload.slice(0, 5));
        streams.push(req);
    }));
    await new Promise(r => setTimeout(r, 30));
    streams.forEach(req => req.end(payload.slice(5)));
    assert.deepEqual((await Promise.all(pending)).sort(), [200, 409]);
});
test('JSON null/array/primitive input is a client error, not a server error', async (t) => { const app = await start(); t.after(app.close); for (const payload of ['null', '[]', '1', '"bad"'])
    assert.equal((await app.req('/api/auth/register', { method: 'POST', body: payload })).status, 400); });
