"""Create a source/artifact submission bundle, excluding secrets and local state."""
import hashlib
import json
import zipfile
from pathlib import Path
from training.audit import ROOT,digest

EXCLUDED={'.git','.venv','tmp','runtime','.pytest_cache','__pycache__','node_modules','.codex','.agents','.aws'}


def main():
    destination=ROOT/'output/release'
    destination.mkdir(parents=True,exist_ok=True)
    files=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():
            continue
        rel=path.relative_to(ROOT)
        if any(part in EXCLUDED for part in rel.parts) or rel.parts[:2]==('output','release'):
            continue
        if path.name.startswith('.env') or path.suffix in ('.env','.sqlite','.sqlite3','.lock') or path.name.endswith(('.sqlite3-wal','.sqlite3-shm')):
            continue
        files.append(path)
    manifest={'artifact':json.loads((ROOT/'artifacts/manifest.json').read_text())['model_version'],
              'bundle_type':'source plus locally verified artifacts; not a Docker image or hosted submission',
              'files':{str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for p in files}}
    (destination/'release_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    archive=destination/'tensorforge_submission.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as zip:
        for file in files:
            zip.write(file,str(file.relative_to(ROOT)).replace('\\','/'))
        zip.write(destination/'release_manifest.json','release_manifest.json')
    with zipfile.ZipFile(archive) as zip:
        assert zip.testzip() is None
        for name,expected in manifest['files'].items():
            assert hashlib.sha256(zip.read(name)).hexdigest()==expected
    print(f'Packaged and hash-verified {len(files)} files, {archive.stat().st_size/1024/1024:.2f} MiB.')


if __name__=='__main__':
    main()
