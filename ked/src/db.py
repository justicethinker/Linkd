import os
import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy database URL
DATABASE_URL = settings.database_url

# Log database connection info (masking sensitive parts)
if DATABASE_URL:
    masked_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL
    logger.info(f"Using PostgreSQL database at {masked_url}")

# create engine with pgvector extension support
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ensure pgvector extension is available when the connection is first created
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        dbapi_connection.commit()
    except Exception as e:
        logger.warning(f"Could not create vector extension: {e}")
        dbapi_connection.rollback()
    finally:
        cursor.close()


def init_db():
    """Initialize the database: create tables, apply RLS, and execute migrations."""
    from . import models  # import models to register them with Base

    # Create all tables first
    Base.metadata.create_all(bind=engine)
    logger.info("Created tables from ORM models")

    # Execute migration SQL files
    _execute_migrations()
    
    # Apply RLS policies
    _apply_rls()
    logger.info("Database initialization complete")


def _execute_migrations():
    """Execute all SQL migration files in the migrations directory."""
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    if not os.path.isdir(migrations_dir):
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])

    with engine.connect() as conn:
        for migration_file in migration_files:
            filepath = os.path.join(migrations_dir, migration_file)
            try:
                with open(filepath, "r") as f:
                    sql_content = f.read()
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
                for statement in statements:
                    conn.execute(text(statement))
                conn.commit()
                logger.info(f"Executed migration: {migration_file}")
            except Exception as e:
                logger.error(f"Error executing migration {migration_file}: {e}")
                conn.rollback()


def _apply_rls():
    """Apply row-level security policies.

    Note: These are also defined in the migration files, but we can re-apply them here
    as an extra safety measure.
    """
    policies = [
        (
            "user_persona",
            "user_isolation_user_persona",
            "user_id = current_setting('app.current_user_id')::int",
        ),
        (
            "interest_nodes",
            "user_isolation_interest_nodes",
            "user_id = current_setting('app.current_user_id')::int",
        ),
        (
            "conversations",
            "user_isolation_conversations",
            "user_id = current_setting('app.current_user_id')::int",
        ),
    ]

    with engine.connect() as conn:
        for table, policy_name, policy_condition in policies:
            try:
                # Enable RLS on the table
                conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
                
                # Try to drop existing policy first (for idempotency)
                try:
                    conn.execute(text(f"DROP POLICY IF EXISTS {policy_name} ON {table};"))
                except Exception:
                    pass  # Policy may not exist
                
                # Create policy
                conn.execute(
                    text(
                        f"CREATE POLICY {policy_name} ON {table} "
                        f"USING ({policy_condition});"
                    )
                )
                conn.commit()
                logger.info(f"Applied RLS policy: {policy_name} on {table}")
            except Exception as e:
                logger.warning(f"Could not apply RLS policy {policy_name}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass


# Redis cache for Phase 2 (Celery task states and temporary data)
try:
    import redis
    # Use full URL if provided, otherwise construct from host/port
    if settings.redis_url:
        redis_cache = redis.from_url(
            settings.redis_url,
            db=2,  # Use DB 2 for application cache (0=broker, 1=result backend)
            decode_responses=True,
            socket_connect_timeout=5,
        )
        logger.info(f"Connected to Redis using URL from REDIS_URL")
    else:
        redis_cache = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=2,  # Use DB 2 for application cache (0=broker, 1=result backend)
            decode_responses=True,
            socket_connect_timeout=5,
        )
        logger.info(f"Connected to Redis at {settings.redis_host}:{settings.redis_port}")
    # Test connection
    redis_cache.ping()
except Exception as e:
    logger.warning(f"Could not connect to Redis: {e}. Caching disabled.")
    redis_cache = None
