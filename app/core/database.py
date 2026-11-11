"""One shared SQLAlchemy engine for all bot modules."""
import ssl
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import DATABASE_URL, EXPECTED_DATABASE_HOST, DATABASE_SCHEMA


def database_options(value: str):
    url = make_url(value)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")
    if url.drivername != "postgresql+asyncpg":
        raise ValueError("Use a PostgreSQL connection string")
    if EXPECTED_DATABASE_HOST and url.host != EXPECTED_DATABASE_HOST:
        raise ValueError("Database host does not match EXPECTED_DATABASE_HOST")
    sslmode = url.query.get("sslmode")
    args = {"statement_cache_size": 0, "prepared_statement_cache_size": 0, "server_settings":{"search_path":DATABASE_SCHEMA}}
    if sslmode in {"require", "verify-ca", "verify-full"}:
        args["ssl"] = ssl.create_default_context()
    elif sslmode and sslmode != "disable":
        raise ValueError("Unsupported sslmode; use require or verify-full for Neon")
    url = url.difference_update_query(["sslmode", "channel_binding"])
    return url, args


def create_db_pool(database_url: str):
    url, connect_args = database_options(database_url)
    new_engine = create_async_engine(url, connect_args=connect_args, pool_size=5,
                                    max_overflow=5, pool_recycle=300, pool_pre_ping=True,
                                    hide_parameters=True, execution_options={"schema_translate_map":{None:DATABASE_SCHEMA}})
    return new_engine, async_sessionmaker(new_engine, class_=AsyncSession, expire_on_commit=False)


engine, session_maker = create_db_pool(DATABASE_URL)


async def assert_database_ready():
    from sqlalchemy import inspect
    from app.features.ticketing.schema import NEW_TABLE_NAMES
    async with engine.connect() as connection:
        names=await connection.run_sync(lambda conn:set(inspect(conn).get_table_names(schema=DATABASE_SCHEMA)))
    missing=set(NEW_TABLE_NAMES)-names
    if missing:
        raise RuntimeError("Database is not migrated; review and apply the integration migration before starting. Missing tables: "+", ".join(sorted(missing)))
