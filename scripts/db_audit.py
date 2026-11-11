"""Read-only schema/count snapshot. Does not dump personal data or modify Alembic."""
import argparse
import asyncio
import json
import hashlib
from pathlib import Path
from sqlalchemy import inspect, text
from app.core.config import APP_ENV, EXPECTED_DATABASE_HOST, DATABASE_SCHEMA
from app.core.database import engine

async def snapshot():
    if APP_ENV != "production" and not EXPECTED_DATABASE_HOST:
        raise SystemExit("EXPECTED_DATABASE_HOST is required before database access")
    async with engine.connect() as connection:
        await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        schema=DATABASE_SCHEMA
        quoted_schema=connection.dialect.identifier_preparer.quote(schema)
        names = await connection.run_sync(lambda conn: inspect(conn).get_table_names(schema=schema))
        await connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
        result = {"database_schema":schema,"tables": {}}
        for name in sorted(names):
            quoted = connection.dialect.identifier_preparer.quote(name)
            count = (await connection.execute(text(f'SELECT COUNT(*) FROM {quoted_schema}.{quoted}'))).scalar_one()
            checksum = hashlib.sha256()
            async for row in await connection.stream(text(f'SELECT md5(row_to_json(t)::text) FROM {quoted_schema}.{quoted} t ORDER BY 1')):
                checksum.update(row[0].encode("ascii"))
            columns = await connection.run_sync(lambda conn, name=name: inspect(conn).get_columns(name,schema=schema))
            result["tables"][name] = {"count":count,"data_sha256":checksum.hexdigest(),"columns":[{"name":column["name"],"nullable":column["nullable"],"type":str(column["type"])} for column in columns]}
        if "alembic_version" in names:
            result["alembic_versions"] = list((await connection.execute(text(f"SELECT version_num FROM {quoted_schema}.alembic_version"))).scalars())
        await connection.rollback()
    await engine.dispose()
    return result


def compare(before, after):
    errors = []
    for name, table in before["tables"].items():
        if name == "alembic_version":
            continue
        current = after["tables"].get(name)
        if current is None:
            errors.append(f"Missing original table: {name}")
        elif current != table:
            errors.append(f"Original table schema/count changed: {name}")
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--compare",type=Path)
    args=parser.parse_args()
    data=asyncio.run(snapshot())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Read-only schema/count audit saved. No personal rows or credentials exported.")
    if args.compare:
        errors=compare(json.loads(args.compare.read_text(encoding="utf-8")),data)
        if errors:
            raise SystemExit("\n".join(errors))
        print("Original table counts and columns are unchanged.")

if __name__ == "__main__":
    main()
