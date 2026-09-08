// Unit tests of the real worker's routing policy. These are not browser/storage
// persistence evidence; browser_http.py exercises native CacheStorage separately.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
const source = await readFile(new URL('../public/sw.js', import.meta.url), 'utf8');
function worker({ offline = false, cached = null } = {}) {
    const listeners = new Map(), writes = [], network = [], waits = [];
    const cache = { put: async (key, response) => writes.push({ key, text: await response.text() }) };
    const scope = {
        URL, Response, console,
        self: { location: new URL('https://masar.example/public/sw.js'), addEventListener: (name, fn) => listeners.set(name, fn) },
        caches: { open: async () => cache, match: async () => cached?.clone() },
        fetch: async request => { network.push(request.url); if (offline) throw Error('origin unavailable'); return new Response('public shell'); }
    };
    vm.runInNewContext(source, scope, { filename: 'public/sw.js' });
    return {
        writes, network,
        async request(path, method = 'GET') {
            let response;
            listeners.get('fetch')({ request: { url: new URL(path, scope.self.location).href, method }, respondWith: promise => { response = promise; }, waitUntil: promise => waits.push(promise) });
            const value = await response;
            await Promise.all(waits);
            return value;
        }
    };
}
test('PWA never intercepts or caches query-bearing review URLs', async () => {
    for (const path of ['/?share=TEST_ONLY', '/?share=', '/src/app.js?share=TEST_ONLY', '/?account=TEST_ONLY']) {
        const w = worker();
        assert.equal(await w.request(path), undefined, path);
        assert.equal(w.writes.length, 0, path);
        assert.equal(w.network.length, 0, path);
    }
});
test('PWA excludes API, unknown, foreign-origin and non-GET requests', async () => {
    for (const [path, method] of [['/api/projects','GET'], ['/api/auth/me','GET'], ['/private.json','GET'], ['https://other.example/src/app.js','GET'], ['/','POST']]) {
        const w = worker(); assert.equal(await w.request(path, method), undefined, path); assert.equal(w.writes.length, 0);
    }
});
test('PWA still serves and caches allowlisted public files', async () => {
    const w = worker(), response = await w.request('/src/app.js');
    assert.equal(await response.text(), 'public shell');
    assert.deepEqual(w.writes, [{ key: '/src/app.js', text: 'public shell' }]);
});
test('PWA network-error fallback returns the existing shell', async () => {
    const w = worker({ offline: true, cached: new Response('cached shell') });
    assert.equal(await (await w.request('/')).text(), 'cached shell');
    assert.equal(w.writes.length, 0);
});
test('PWA never fabricates a successful page when its shell is missing', async () => {
    const w = worker({ offline: true }), response = await w.request('/');
    assert.equal(response.status, 503); assert.match(await response.text(), /asset unavailable/);
});
