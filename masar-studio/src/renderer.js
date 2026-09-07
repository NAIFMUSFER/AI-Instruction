import { sceneBoxes } from '../shared/geometry.js';
// A small dependency-free WebGL renderer. No runtime CDN, eval, external assets, or hidden model mutation.
const vsub = (a, b) => a.map((x, i) => x - b[i]), dot = (a, b) => a.reduce((s, x, i) => s + x * b[i], 0), cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]], norm = a => { const n = Math.hypot(...a) || 1; return a.map(x => x / n); };
const mul = (a, b) => { const c = new Float32Array(16); for (let j = 0; j < 4; j++)
    for (let i = 0; i < 4; i++)
        for (let k = 0; k < 4; k++)
            c[j * 4 + i] += a[k * 4 + i] * b[j * 4 + k]; return c; };
function perspective(fov, aspect, near, far) { const f = 1 / Math.tan(fov / 2), nf = 1 / (near - far); return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0]); }
function lookAt(eye, target) { const z = norm(vsub(eye, target)), x = norm(cross([0, 1, 0], z)), y = cross(z, x); return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -dot(x, eye), -dot(y, eye), -dot(z, eye), 1]); }
function rayBox(origin, dir, min, max) { let lo = -Infinity, hi = Infinity; for (let i = 0; i < 3; i++) {
    if (Math.abs(dir[i]) < 1e-9) {
        if (origin[i] < min[i] || origin[i] > max[i])
            return null;
        continue;
    }
    const a = (min[i] - origin[i]) / dir[i], b = (max[i] - origin[i]) / dir[i];
    lo = Math.max(lo, Math.min(a, b));
    hi = Math.min(hi, Math.max(a, b));
    if (hi < lo)
        return null;
} return hi >= Math.max(0, lo) ? Math.max(0, lo) : null; }
export class StudioRenderer {
    constructor(canvas, onSelect, onError = () => { }) {
        this.canvas = canvas;
        this.onSelect = onSelect;
        this.onError = onError;
        this.theta = .64;
        this.phi = .80;
        this.radius = 36;
        this.target = [10, 0, -12.5];
        this.options = {};
        this.disposed = false;
        this.autoFit = true;
        this.lastAspect = null;
        const gl = canvas.getContext('webgl', { antialias: true, alpha: false, preserveDrawingBuffer: true });
        this.gl = gl;
        this.ctx = gl ? null : canvas.getContext('2d');
        if (!gl && !this.ctx)
            throw Error('تعذّر فتح مساحة الرسم. المخطط ثنائي الأبعاد يظل متاحًا.');
        this.software = !gl;
        canvas.dataset.renderer = gl ? 'webgl' : 'canvas3d';
        if (gl) {
            const shader = (type, source) => { const s = gl.createShader(type); gl.shaderSource(s, source); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS))
                throw Error('تعذّر إعداد العرض ثلاثي الأبعاد.'); return s; };
            const vs = shader(gl.VERTEX_SHADER, 'attribute vec3 aPosition;attribute vec3 aColor;attribute vec3 aNormal;uniform mat4 uMatrix;varying vec3 vColor;void main(){float light=.65+.35*max(dot(normalize(aNormal),normalize(vec3(.6,1.,.45))),0.);vColor=aColor*light;gl_Position=uMatrix*vec4(aPosition,1.);}');
            const fs = shader(gl.FRAGMENT_SHADER, 'precision mediump float;varying vec3 vColor;void main(){gl_FragColor=vec4(vColor,1.);}');
            const p = gl.createProgram();
            gl.attachShader(p, vs);
            gl.attachShader(p, fs);
            gl.linkProgram(p);
            gl.deleteShader(vs);
            gl.deleteShader(fs);
            if (!gl.getProgramParameter(p, gl.LINK_STATUS))
                throw Error('تعذّر تشغيل العرض ثلاثي الأبعاد.');
            this.program = p;
            this.buffer = gl.createBuffer();
            this.uMatrix = gl.getUniformLocation(p, 'uMatrix');
            this.attrs = ['aPosition', 'aColor', 'aNormal'].map(n => gl.getAttribLocation(p, n));
            gl.enable(gl.DEPTH_TEST);
            gl.clearColor(.92, .94, .90, 1);
        }
        this.down = e => { if (e.button !== 0)
            return; canvas.setPointerCapture(e.pointerId); this.pointer = { x: e.clientX, y: e.clientY, ox: e.clientX, oy: e.clientY, moved: false }; };
        this.move = e => { if (!this.pointer)
            return; const p = this.pointer, dx = e.clientX - p.x, dy = e.clientY - p.y; if (Math.hypot(e.clientX - p.ox, e.clientY - p.oy) > 5)
            p.moved = true; if (p.moved) {
            this.theta -= dx * .008;
            this.phi = Math.max(.15, Math.min(1.48, this.phi + dy * .006));
            this.draw();
        } p.x = e.clientX; p.y = e.clientY; };
        this.up = e => { if (this.pointer && !this.pointer.moved)
            this.pick(e.clientX, e.clientY); this.pointer = null; };
        this.cancel = () => { this.pointer = null; };
        this.wheel = e => { e.preventDefault(); this.zoom(Math.exp(e.deltaY * .001)); };
        this.key = e => { if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', '+', '-', 'Home'].includes(e.key)) {
            e.preventDefault();
            if (e.key === 'ArrowLeft')
                this.theta += .12;
            if (e.key === 'ArrowRight')
                this.theta -= .12;
            if (e.key === 'ArrowUp')
                this.phi = Math.max(.15, this.phi - .08);
            if (e.key === 'ArrowDown')
                this.phi = Math.min(1.48, this.phi + .08);
            if (e.key === '+')
                this.radius *= .9;
            if (e.key === '-')
                this.radius *= 1.1;
            if (e.key === 'Home')
                this.reset();
            this.draw();
        } };
        this.lost = e => { e.preventDefault(); this.onError('توقف سياق العرض ثلاثي الأبعاد. استخدم المخطط أو أعد تحميل الصفحة.'); };
        canvas.addEventListener('pointerdown', this.down);
        canvas.addEventListener('pointermove', this.move);
        canvas.addEventListener('pointerup', this.up);
        canvas.addEventListener('pointercancel', this.cancel);
        canvas.addEventListener('wheel', this.wheel, { passive: false });
        canvas.addEventListener('keydown', this.key);
        canvas.addEventListener('webglcontextlost', this.lost);
        this.observer = new ResizeObserver(() => this.draw());
        this.observer.observe(canvas);
        canvas.dataset.ready = 'true';
    }
    setModel(model, options = {}) { const isNew = this.model?.id !== model.id; this.model = model; this.options = options; if (isNew)
        this.reset(false); this.rebuild(); this.draw(); }
    reset(draw = true) { if (this.model) {
        const { width: w, depth: d } = this.model.site;
        const aspect = this.canvas.clientWidth / Math.max(1, this.canvas.clientHeight) || 1;
        this.radius = Math.hypot(w, d) * .56 / Math.sin(Math.min(.67, 2 * Math.atan(Math.tan(.67 / 2) * aspect)) / 2);
        this.lastAspect = aspect;
        this.autoFit = true;
        this.target = [w / 2, this.options.all ? this.model.levels.length * 1.0 : 0, -d / 2];
    } this.theta = .64; this.phi = .80; if (draw)
        this.draw(); }
    zoom(scale) { this.autoFit = false; this.radius = Math.max(5, Math.min(500, this.radius * scale)); this.draw(); }
    rebuild() {
        const data = [], boxes = sceneBoxes(this.model, this.options);
        this.boxes = boxes;
        if (this.software)
            return;
        const faces = [{ p: [0, 1, 2, 0, 2, 3], n: [0, 0, 1] }, { p: [5, 4, 7, 5, 7, 6], n: [0, 0, -1] }, { p: [4, 0, 3, 4, 3, 7], n: [-1, 0, 0] }, { p: [1, 5, 6, 1, 6, 2], n: [1, 0, 0] }, { p: [3, 2, 6, 3, 6, 7], n: [0, 1, 0] }, { p: [4, 5, 1, 4, 1, 0], n: [0, -1, 0] }];
        for (const b of boxes) {
            const { x, y, z, w, d, h } = b;
            const pos = [[x, z, -y], [x + w, z, -y], [x + w, z + h, -y], [x, z + h, -y], [x, z, -y - d], [x + w, z, -y - d], [x + w, z + h, -y - d], [x, z + h, -y - d]];
            const hex = b.color || '#ddd5c6', col = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255);
            for (const f of faces)
                for (const i of f.p)
                    data.push(...pos[i], ...col, ...f.n);
        }
        this.count = data.length / 9;
        this.gl.bindBuffer(this.gl.ARRAY_BUFFER, this.buffer);
        this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array(data), this.gl.STATIC_DRAW);
    }
    draw() { if (this.disposed || !this.model)
        return; const { canvas: c, gl } = this, w = c.clientWidth, h = c.clientHeight; if (!w || !h)
        return; if (this.autoFit && Math.abs(w / h - (this.lastAspect || 0)) > .01)
        this.reset(false); const ratio = Math.min(globalThis.devicePixelRatio || 1, 2), pw = Math.round(w * ratio), ph = Math.round(h * ratio); if (c.width !== pw || c.height !== ph) {
        c.width = pw;
        c.height = ph;
    } if (gl) {
        gl.viewport(0, 0, pw, ph);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    } this.eye = [this.target[0] + this.radius * Math.sin(this.phi) * Math.cos(this.theta), this.target[1] + this.radius * Math.cos(this.phi), this.target[2] + this.radius * Math.sin(this.phi) * Math.sin(this.theta)]; this.matrix = mul(perspective(.67, w / h, .1, 2000), lookAt(this.eye, this.target)); if (this.software) {
        this.drawSoftware(w, h, ratio);
        return;
    } gl.useProgram(this.program); gl.uniformMatrix4fv(this.uMatrix, false, this.matrix); gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer); for (let i = 0; i < 3; i++) {
        gl.enableVertexAttribArray(this.attrs[i]);
        gl.vertexAttribPointer(this.attrs[i], 3, gl.FLOAT, false, 36, i * 12);
    } gl.drawArrays(gl.TRIANGLES, 0, this.count); }
    drawSoftware(width, height, ratio) {
        const ctx = this.ctx;
        ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
        ctx.fillStyle = '#ebf0e5';
        ctx.fillRect(0, 0, width, height);
        const project = p => { const m = this.matrix, x = p[0], y = p[1], z = p[2], w = m[3] * x + m[7] * y + m[11] * z + m[15]; if (w <= 0)
            return null; return [(m[0] * x + m[4] * y + m[8] * z + m[12]) / w * width / 2 + width / 2, height / 2 - (m[1] * x + m[5] * y + m[9] * z + m[13]) / w * height / 2]; };
        const definitions = [{ p: [0, 1, 2, 3], n: [0, 0, 1] }, { p: [5, 4, 7, 6], n: [0, 0, -1] }, { p: [4, 0, 3, 7], n: [-1, 0, 0] }, { p: [1, 5, 6, 2], n: [1, 0, 0] }, { p: [3, 2, 6, 7], n: [0, 1, 0] }, { p: [4, 5, 1, 0], n: [0, -1, 0] }], faces = [], forward = norm(vsub(this.target, this.eye)), light = norm([.6, 1, .45]);
        for (const box of this.boxes) {
            const { x, y, z, w, d, h } = box, vertices = [[x, z, -y], [x + w, z, -y], [x + w, z + h, -y], [x, z + h, -y], [x, z, -y - d], [x + w, z, -y - d], [x + w, z + h, -y - d], [x, z + h, -y - d]], hex = box.color || '#ddd5c6', color = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
            for (const face of definitions) {
                const points = face.p.map(i => vertices[i]), center = [0, 1, 2].map(i => points.reduce((sum, p) => sum + p[i], 0) / 4);
                if (dot(face.n, vsub(this.eye, center)) <= 0)
                    continue;
                const projected = points.map(project);
                if (projected.some(p => !p))
                    continue;
                const intensity = .65 + .35 * Math.max(0, dot(face.n, light));
                faces.push({ priority: box.kind === 'ground' ? -2 : box.kind === 'paving' ? -1 : 0, points: projected, depth: dot(vsub(center, this.eye), forward), color: `rgb(${color.map(v => Math.round(v * intensity)).join(',')})` });
            }
        }
        faces.sort((a, b) => a.priority - b.priority || b.depth - a.depth);
        for (const face of faces) {
            ctx.beginPath();
            ctx.moveTo(...face.points[0]);
            for (const p of face.points.slice(1))
                ctx.lineTo(...p);
            ctx.closePath();
            ctx.fillStyle = face.color;
            ctx.fill();
            ctx.strokeStyle = 'rgba(41,61,38,0.08)';
            ctx.lineWidth = .35;
            ctx.stroke();
        }
    }
    pick(clientX, clientY) { if (!this.model)
        return; const rect = this.canvas.getBoundingClientRect(), nx = (clientX - rect.left) / rect.width * 2 - 1, ny = 1 - (clientY - rect.top) / rect.height * 2; const f = norm(vsub(this.target, this.eye)), r = norm(cross(f, [0, 1, 0])), u = cross(r, f), tan = Math.tan(.67 / 2), aspect = rect.width / rect.height, dir = norm(f.map((v, i) => v + r[i] * nx * tan * aspect + u[i] * ny * tan)); let best = null, dist = Infinity; for (const l of this.model.levels) {
        if (!this.options.all && l.id !== this.options.levelId)
            continue;
        const elevation = this.options.all ? l.elevation : 0;
        for (const room of l.rooms) {
            const t = rayBox(this.eye, dir, [room.x, elevation, -room.y - room.d], [room.x + room.w, elevation + 1.1, -room.y]);
            if (t !== null && t < dist) {
                dist = t;
                best = room.id;
            }
        }
    } if (best)
        this.onSelect(best); }
    dispose() { this.disposed = true; this.observer.disconnect(); const c = this.canvas; for (const [name, fn] of [['pointerdown', this.down], ['pointermove', this.move], ['pointerup', this.up], ['pointercancel', this.cancel], ['wheel', this.wheel], ['keydown', this.key], ['webglcontextlost', this.lost]])
        c.removeEventListener(name, fn); if (this.gl) {
        this.gl.deleteBuffer(this.buffer);
        this.gl.deleteProgram(this.program);
    } }
}
