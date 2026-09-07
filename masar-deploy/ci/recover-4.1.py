"""Materialize exact MASAR 4.1 source from verified transport and historical prefix."""
import argparse,base64,hashlib,io,json,lzma,os,shutil,tarfile,tempfile,zlib
from pathlib import Path,PurePosixPath
p=argparse.ArgumentParser();p.add_argument('--payload',required=True);p.add_argument('--base',required=True);p.add_argument('--contract',required=True);p.add_argument('--dest',required=True);args=p.parse_args()
payload=Path(args.payload);old=Path(args.base);target=Path(args.dest).resolve();contract=json.loads(Path(args.contract).read_text())
hash=lambda b:hashlib.sha256(b).hexdigest()
assert contract['format']=='masar-source-recovery-1' and contract['version']=='4.1.0'
assert {x.name for x in payload.glob('part-*')}==set(contract['parts']),'Missing/unexpected transport parts'
encoded=[]
for name,expected in sorted(contract['parts'].items()):
    data=(payload/name).read_bytes();assert hash(data)==expected,name;encoded.append(data)
packed=base64.b64decode(b''.join(encoded),validate=True);assert len(packed)==contract['compressedBytes'];assert hash(packed)==contract['compressedSha256']
decoder=lzma.LZMADecompressor();raw=decoder.decompress(packed,max_length=2000000);assert decoder.eof and not decoder.unused_data;assert len(raw)==contract['decodedJsonBytes']
manifest=json.loads(raw);encoded=[]
assert {x.name for x in old.glob('part-*')}==set(manifest['baseParts']),'Legacy recovery prefix changed'
for name,expected in sorted(manifest['baseParts'].items()):
    data=(old/name).read_bytes();assert hash(data)==expected,name;encoded.append(data)
compressed=base64.b64decode(b''.join(encoded),validate=True);assert hash(compressed)==manifest['baseCompressedSha256']
gzip=zlib.decompressobj(31);prefix=gzip.decompress(compressed,5000000);assert len(prefix)==manifest['baseRawBytes']
baseline={}
with tarfile.open(fileobj=io.BytesIO(prefix),mode='r:') as archive:
    try:
        for member in archive:
            if member.isfile():baseline[member.name.removeprefix('./')]=prefix[member.offset_data:min(member.offset_data+member.size,len(prefix))]
    except tarfile.ReadError: pass
assert len(manifest['files'])==contract['sourceFileCount']
assert not target.exists(),'Refusing to overwrite existing source directory'
target.parent.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.masar-recovery-',dir=target.parent));names=set();tree=[]
try:
    for record in manifest['files']:
        name=record['path'];path=PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts and '\\' not in name and name not in names
        assert name!='.env' and (not name.startswith('.env.') or name=='.env.example')
        names.add(name);base=baseline.get(name,b'');assert hash(base)==record['baseSha256'],name
        lines=base.splitlines(keepends=True);pieces=[]
        for op in record['ops']:
            if op[0]==0:
                assert len(op)==3 and all(type(n) is int for n in op) and 0<=op[1]<=op[2]<=len(lines);pieces.append(b''.join(lines[op[1]:op[2]]))
            else:
                assert op[0]==1 and len(op)==2 and isinstance(op[1],str);pieces.append(op[1].encode('utf8'))
        data=b''.join(pieces);assert len(data)==record['bytes'] and hash(data)==record['sha256'],name
        file=stage/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data);tree.append(name+' '+hash(data)+'\n')
    assert hash(''.join(tree).encode())==contract['sourceTreeSha256']
    os.rename(stage,target)
except BaseException:
    shutil.rmtree(stage,ignore_errors=True);raise
print(json.dumps({'status':'PASS','sourceFiles':len(names),'sourceTreeSha256':contract['sourceTreeSha256'],'destination':str(target),'legacyGzipComplete':gzip.eof,'productionUsesTransport':False}))
