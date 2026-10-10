"""Run required checks and persist exact output/exit codes (including failures)."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from training.audit import ROOT


def main():
    records=[]
    commands=[[sys.executable,'-m','pytest','-q','--disable-warnings'], [sys.executable,'-m','scripts.offline_smoke'], [sys.executable,'-m','pip','check']]
    for command in commands:
        process=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        records.append({'command':command,'exit_code':process.returncode,'stdout':process.stdout,'stderr':process.stderr})
        print(process.stdout,flush=True)
        if process.stderr:
            print(process.stderr,flush=True)
    report={'time_utc':datetime.now(timezone.utc).isoformat(),'checks':records}
    directory=ROOT/'experiments'
    (directory/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (directory/'verification_history.jsonl').open('a',encoding='utf-8').write(json.dumps(report)+'\n')
    if any(r['exit_code'] for r in records):
        raise SystemExit(1)


if __name__=='__main__':
    main()
