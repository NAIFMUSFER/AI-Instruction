import { readdir, readFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
for (const dir of ['shared', 'src', 'server', 'tools', 'tests'])
    for (const f of await readdir(dir)) {
        if (!/\.m?js$/.test(f))
            continue;
        const result = spawnSync(process.execPath, ['--check', dir + '/' + f], { encoding: 'utf8' });
        if (result.status) {
            console.error(result.stderr);
            process.exit(1);
        }
    }
const html = await readFile('public/index.html', 'utf8');
if (/\son[a-z]+\s*=/.test(html) || /<script(?![^>]+src=)[^>]*>/.test(html))
    throw Error('Executable inline script found in served HTML');
console.log('PASS: JavaScript syntax and served HTML script policy.');
