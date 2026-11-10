"""Executable negative witnesses for release evidence, packaging, and diagnostics."""
import io
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import acs_rate_limit as RL


def receipt(browser=False, status='PASS'):
    groups = ['C', 'D', 'E', 'F', 'G(browser)'] if browser else ['A', 'B', 'G']
    checks = [{'group': group, 'id': group + '1', 'status': status} for group in groups]
    return {'schema': 'acs-production-verification/1.0.0',
            'frontend': 'https://frontend.example', 'backend': 'https://backend.example',
            'groups': groups, 'checks': checks, 'observed': {'frontend_sha': 'a'*40, 'backend_sha': 'a'*40},
            'counts': {'pass': len(checks) if status == 'PASS' else 0,
                       'fail': len(checks) if status == 'FAIL' else 0,
                       'not_verified': len(checks) if status == 'NOT VERIFIED' else 0,
                       'total': len(checks)},
            'exit_code': {'PASS': 0, 'FAIL': 1, 'NOT VERIFIED': 2}[status],
            'verdict': status}


class ReleaseSafety(unittest.TestCase):
    def run_gate(self, behavior='success', http_behavior='success'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); dest = root / 'tests/production'; dest.mkdir(parents=True)
            shutil.copy(ROOT/'tests/production/run_all.sh', dest/'run_all.sh')
            helper = ROOT/'tests/production/validate_evidence.py'
            if helper.exists(): shutil.copy(helper, dest/helper.name)
            for browser, mode in [(False, http_behavior), (True, behavior)]:
                out = 'verify_live_browser.json' if browser else 'verify_live.json'
                data = receipt(browser, 'NOT VERIFIED' if mode == 'not_verified' else 'FAIL' if mode == 'fail' else 'PASS')
                if mode == 'partial':
                    data['checks'][0]['status'] = 'NOT VERIFIED'; data['counts']['pass'] -= 1; data['counts']['not_verified'] += 1
                if mode == 'missing_group':
                    data['checks'].pop(); data['counts']['pass'] -= 1; data['counts']['total'] -= 1
                body = json.dumps(data)
                if browser:
                    source = "const fs=require('fs');fs.mkdirSync(__dirname+'/outputs',{recursive:true});"
                    if mode == 'crash': source += "throw new Error('SYNTHETIC_CRASH');"
                    elif mode == 'signal': source += "process.kill(process.pid,'SIGTERM');"
                    elif mode != 'missing': source += "fs.writeFileSync(__dirname+'/outputs/"+out+"',"+json.dumps('bad json' if mode=='malformed' else body)+");"
                    source += "process.exit("+str(data['exit_code'])+");"
                    (dest/'verify_live_browser.js').write_text(source)
                else:
                    source = "import json\nfrom pathlib import Path\nimport sys\np=Path(__file__).parent/'outputs'\np.mkdir(exist_ok=True)\n"
                    if mode == 'crash': source += "raise RuntimeError('SYNTHETIC_CRASH')\n"
                    elif mode != 'missing': source += "(p/'"+out+"').write_text("+repr('bad json' if mode=='malformed' else body)+")\n"
                    source += 'sys.exit('+str(data['exit_code'])+')\n'
                    (dest/'verify_live.py').write_text(source)
            result = subprocess.run(['sh',str(dest/'run_all.sh')], text=True, capture_output=True)
            path = dest/'outputs/summary.json'
            summary = json.loads(path.read_text()) if path.exists() else {}
            return result.returncode, summary, result.stdout[-2000:]

    def test_complete_evidence_passes(self):
        rc, summary, log = self.run_gate()
        self.assertEqual(rc, 0, log); self.assertEqual(summary['verdict'], 'PASS')

    def test_crash_missing_partial_or_not_verified_never_pass(self):
        for mode in ['crash','signal','missing','malformed','not_verified','partial','fail','missing_group']:
            with self.subTest(mode=mode):
                rc, summary, log = self.run_gate(mode)
                self.assertNotEqual(rc, 0, log)
                self.assertNotEqual(summary.get('verdict'), 'PASS', log)

    def test_http_crash_never_passes(self):
        rc, summary, log = self.run_gate(http_behavior='crash')
        self.assertNotEqual(rc, 0, log); self.assertNotEqual(summary.get('verdict'), 'PASS')

    def test_release_manifest_excludes_synthetic_secrets(self):
        helper = ROOT/'tools/release_manifest.py'
        self.assertTrue(helper.exists(), 'release archive must have a tracked-file manifest implementation')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'repo'; root.mkdir(); archive = Path(tmp)/'release.zip'
            for name in ['public/index.html','public/vendor/three/build/three.module.js','acs_server.py','requirements.txt',
                         '.env','.env.production','credentials.json','private.pem','tests/production/outputs/capture.png']:
                path=root/name; path.parent.mkdir(parents=True,exist_ok=True);path.write_text('SYNTHETIC_SENTINEL')
            subprocess.run(['git','init','-q',str(root)],check=True)
            subprocess.run(['git','-C',str(root),'add','--all'],check=True)
            for name in ['untracked.sqlite','untracked.log','screenshot.png']:(root/name).write_text('SYNTHETIC_SENTINEL')
            result=subprocess.run([sys.executable,str(helper),'--root',str(root),'--output',str(archive)],text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with zipfile.ZipFile(archive) as z:
                names=set(z.namelist())
                self.assertTrue({'public/index.html','public/vendor/three/build/three.module.js','acs_server.py','requirements.txt','RELEASE-MANIFEST.json'} <= names)
                self.assertFalse(any('.git/' in n or n.startswith('.env') or 'credentials' in n or n.endswith(('.pem','.sqlite','.log')) or 'outputs/' in n for n in names),names)
                manifest=json.loads(z.read('RELEASE-MANIFEST.json'))
                self.assertTrue(manifest['files']);self.assertTrue(all('sha256' in row for row in manifest['files']))

    def test_raw_diagnostics_never_reach_logs(self):
        sentinel='SYNTHETIC_PAYLOAD redis://user:SYNTHETIC_PASSWORD@secret.invalid Bearer SYNTHETIC_TOKEN'
        class Broken:
            name='redis'; distributed=True
            def hit(self,*args,**kwargs):raise RuntimeError(sentinel)
            def healthy(self):raise RuntimeError(sentinel)
        capture=io.StringIO();handler=logging.StreamHandler(capture);RL.LOG.addHandler(handler)
        try:
            lim=RL.RateLimiter(backend=Broken(),fail_policy='closed')
            self.assertFalse(lim.check('synthetic')['allowed'])
            RL.health_status(limiter=lim,env={})
            RL.RedisBackend(type('Client',(),{'ping':lambda self: (_ for _ in ()).throw(RuntimeError(sentinel))})()).healthy()
            RL.env_int('TEST',1,env={'TEST':sentinel});RL.backend_choice({'ACS_RATE_LIMIT_BACKEND':sentinel})
        finally:RL.LOG.removeHandler(handler)
        self.assertNotIn('SYNTHETIC_',capture.getvalue());self.assertIn('RuntimeError',capture.getvalue())


if __name__ == '__main__':unittest.main(verbosity=2)
