import sys
import logging

try:
    import sqlite3  # noqa: F401
except ImportError:
    import pysqlite3 as sqlite3
    sys.modules["sqlite3"] = sqlite3

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def get_engine(url: str = None):
    """Create a SQLAlchemy engine."""
    db_url = url or settings.DATABASE_URL
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(db_url, echo=settings.DEBUG, connect_args=connect_args)


# Default engine and session (lazy - won't fail if DB isn't available)
_engine = None
_SessionLocal = None


def get_session_local():
    """Get or create the default SessionLocal."""
    global _engine, _SessionLocal
    if _engine is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _SessionLocal


def get_db():
    """Dependency that provides a database session per request."""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(url: str = None):
    """Create all tables. Used in development/testing only."""
    engine = get_engine(url) if url else get_engine()
    Base.metadata.create_all(bind=engine)
    return engine


def auto_migrate_columns(engine):
    """
    Auto-add missing columns to existing tables.
    
    This function inspects the database and compares it with SQLAlchemy models.
    For any missing columns, it generates and executes ALTER TABLE statements.
    This enables automatic schema evolution as new columns are added to models.
    """
    inspector = inspect(engine)
    
    # Get all models from Base.metadata
    for table_name, table in Base.metadata.tables.items():
        if not inspector.has_table(table_name):
            # Table doesn't exist yet, create_all will handle it
            continue
        
        # Get existing columns in the database
        existing_columns = {col['name'] for col in inspector.get_columns(table_name)}
        
        # Check each column defined in the model
        for column in table.columns:
            if column.name not in existing_columns:
                # Build the column type string for the target database dialect
                col_type = column.type.compile(engine.dialect)
                
                # Build the NOT NULL constraint
                nullable_clause = "" if column.nullable else " NOT NULL"
                
                # Build the DEFAULT clause - try server_default first (preferred for migrations)
                default_clause = ""
                if column.server_default is not None:
                    # Use server_default value if available - this is the DB-side default
                    try:
                        server_default_val = column.server_default.arg
                        if isinstance(server_default_val, str):
                            default_clause = f" DEFAULT '{server_default_val}'"
                        elif hasattr(server_default_val, 'compile'):
                            # Handle SQLAlchemy functions like func.now()
                            compiled = server_default_val.compile(engine.dialect)
                            default_clause = f" DEFAULT {compiled}"
                        elif server_default_val is not None:
                            default_clause = f" DEFAULT {server_default_val}"
                    except Exception as e:
                        logger.debug(f"Could not extract server_default for {table_name}.{column.name}: {e}")
                elif column.default is not None:
                    # Fall back to Python-side default if no server_default
                    try:
                        default_val = column.default.arg
                        if not callable(default_val):
                            if isinstance(default_val, str):
                                default_clause = f" DEFAULT '{default_val}'"
                            elif default_val is not None:
                                default_clause = f" DEFAULT {default_val}"
                    except Exception as e:
                        logger.debug(f"Could not extract default for {table_name}.{column.name}: {e}")
                
                # Build and execute the ALTER TABLE statement
                alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}{nullable_clause}{default_clause}"
                
                try:
                    with engine.begin() as conn:
                        conn.execute(text(alter_sql))
                    logger.info(f"✓ Added column: {table_name}.{column.name}")
                except Exception as e:
                    logger.warning(f"Could not add column {table_name}.{column.name}: {e}")

