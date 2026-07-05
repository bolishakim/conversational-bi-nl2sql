"""
Database Connection Utilities
Extracted from research prototype: rag_nl2sql_system/utils/database.py
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager, asynccontextmanager
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config import settings


class DatabaseConnection:
    """PostgreSQL database connection manager"""

    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        """
        Initialize database connection

        Args:
            host: Database host
            port: Database port
            dbname: Database name
            user: Database user
            password: Database password
        """
        self.conn_params = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
            "password": password,
        }

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(**self.conn_params)
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @contextmanager
    def get_cursor(self, cursor_factory=RealDictCursor):
        """Context manager for database cursors"""
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            return cursor.rowcount

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False

    def setup_pgvector(self) -> bool:
        """Set up pgvector extension"""
        try:
            with self.get_cursor() as cursor:
                # Create extension if not exists
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                print(" pgvector extension created/verified")
                return True
        except Exception as e:
            print(f" Failed to set up pgvector: {e}")
            return False

    def create_embeddings_table(self, embedding_dimensions: int = 1536) -> bool:
        """Create table to store table embeddings"""
        try:
            with self.get_cursor() as cursor:
                # Create schema if not exists
                cursor.execute("CREATE SCHEMA IF NOT EXISTS rag;")

                # Drop existing table if exists
                cursor.execute("DROP TABLE IF EXISTS rag.table_embeddings CASCADE;")

                # Create table with vector column
                cursor.execute(f"""
                    CREATE TABLE rag.table_embeddings (
                        id SERIAL PRIMARY KEY,
                        schema_name TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        full_name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        business_terms TEXT[] NOT NULL,
                        common_questions TEXT[] NOT NULL,
                        key_columns JSONB NOT NULL,
                        sample_values JSONB,
                        row_count INTEGER,
                        tier INTEGER NOT NULL,
                        embedding_text TEXT NOT NULL,
                        embedding vector({embedding_dimensions}),
                        created_at TIMESTAMP DEFAULT NOW(),
                        UNIQUE(schema_name, table_name)
                    );
                """)

                # Create vector index for fast similarity search
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS table_embeddings_vector_idx
                    ON rag.table_embeddings
                    USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """)

                # Create regular indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS table_embeddings_tier_idx
                    ON rag.table_embeddings(tier);
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS table_embeddings_schema_idx
                    ON rag.table_embeddings(schema_name);
                """)

                print(" Embeddings table created successfully")
                return True
        except Exception as e:
            print(f" Failed to create embeddings table: {e}")
            return False

    def get_table_count(self) -> int:
        """Get count of embedded tables"""
        with self.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM rag.table_embeddings;")
            result = cursor.fetchone()
            return result['count'] if result else 0


# ============================================================================
# Async SQLAlchemy Session Management
# ============================================================================

# Create async engine
async_engine = create_async_engine(
    settings.async_database_url,
    echo=False,
    pool_size=10,
    max_overflow=20
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@asynccontextmanager
async def get_db_session():
    """
    Async context manager for database sessions

    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
