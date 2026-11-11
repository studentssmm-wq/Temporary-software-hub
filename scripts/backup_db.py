"""Create a local PostgreSQL custom-format backup without putting passwords in arguments."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
from sqlalchemy.engine import make_url
from app.core.config import APP_ENV, DATABASE_URL, EXPECTED_DATABASE_HOST


def backup(output: Path, allow_production=False):
    if output.exists():
        raise RuntimeError("Backup file already exists; choose a new filename to preserve it")
    url=make_url(DATABASE_URL)
    if not EXPECTED_DATABASE_HOST or url.host!=EXPECTED_DATABASE_HOST or (APP_ENV=="production" and not allow_production):
        raise RuntimeError("Verify EXPECTED_DATABASE_HOST and use --allow-production for an explicit production backup")
    binary=shutil.which("pg_dump")
    if binary is None:
        candidates=[]
        for base in [Path("C:/Program Files/PostgreSQL"),Path("C:/Program Files (x86)/PostgreSQL")]:
            if base.exists():
                candidates.extend(base.glob("*/bin/pg_dump.exe"))
        if candidates:
            binary=str(sorted(candidates,key=lambda p:tuple(int(part) for part in p.parents[1].name.split(".") if part.isdigit()),reverse=True)[0])
    if not binary:
        raise RuntimeError("pg_dump not found. Install PostgreSQL client tools before migration")
    output.parent.mkdir(parents=True,exist_ok=True)
    env={**os.environ,"PGHOST":url.host,"PGPORT":str(url.port or 5432),"PGDATABASE":url.database or "neondb", "PGUSER":url.username or "", "PGPASSWORD":url.password or "", "PGSSLMODE":"disable" if url.host=="127.0.0.1" else "require"}
    result=subprocess.run([binary,"--format=custom","--no-owner","--no-acl","--file",str(output)],env=env,capture_output=True)
    if result.returncode:
        if output.exists():
            output.unlink()
        raise RuntimeError("pg_dump failed. Check connectivity and pg_dump/server version compatibility; credentials omitted")
    restore=Path(binary).with_name("pg_restore.exe" if os.name=="nt" else "pg_restore")
    check=subprocess.run([str(restore),"--list",str(output)],capture_output=True)
    if check.returncode or not output.stat().st_size:
        raise RuntimeError("Backup archive failed validation")
    print("Local backup created and its archive catalog verified")

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--allow-production",action="store_true")
    args=parser.parse_args()
    backup(args.output,args.allow_production)
