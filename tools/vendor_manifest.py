"""Record exact copies from integrity-installed npm packages, not arbitrary locals."""
import hashlib
import json
from pathlib import Path


def write(root):
    lock=json.loads((root/'package-lock.json').read_text())
    rows=[]
    for package, paths in [('three',['build/three.module.js','examples/jsm']),('pdfjs-dist',['build/pdf.min.mjs','build/pdf.worker.min.mjs'])]:
        info=lock['packages']['node_modules/'+package]
        source=root/'node_modules'/package
        if json.loads((source/'package.json').read_text())['version']!=info['version']:raise ValueError('VENDOR_VERSION_MISMATCH')
        target=root/'public/vendor'/((('pdfjs' if package=='pdfjs-dist' else package)+'@'+info['version']))
        for relative in paths:
            path=source/relative
            files=sorted(path.rglob('*')) if path.is_dir() else [path]
            for src in files:
                if src.is_dir():continue
                if src.is_symlink():raise ValueError('VENDOR_SYMLINK_REJECTED')
                rel=src.relative_to(source)
                dest=target/(rel.name if package=='pdfjs-dist' else rel)
                if not dest.is_file() or src.read_bytes()!=dest.read_bytes():raise ValueError('VENDOR_COPY_MISMATCH: '+str(rel))
                rows.append({'path':dest.relative_to(root).as_posix(),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'package':package,'version':info['version'],'integrity':info['integrity']})
    (root/'public/vendor/manifest.json').write_text(json.dumps({'schema':'acs-vendor-manifest/1.0','files':rows},indent=2)+'\n')
    print('Verified vendor manifest: %d exact package files' % len(rows))


if __name__=='__main__':write(Path(__file__).resolve().parents[1])
