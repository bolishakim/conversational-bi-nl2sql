"""
Database connection utilities for RAG retrieval
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any
from config import settings


class DatabaseConnection:
    """PostgreSQL database connection manager for RAG queries"""

    def __init__(self):
        self.database_url = settings.database_url

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = psycopg2.connect(self.database_url)
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

    def execute_raw(self, sql: str) -> None:
        """Execute raw SQL statements (for migrations, DDL, etc.)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql)
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False


# Global database instance
db = DatabaseConnection()


def get_db_connection():
    """
    Get a raw database connection for SQL execution

    Returns:
        psycopg2 connection object

    Note: Caller is responsible for closing the connection
    """
    return psycopg2.connect(settings.database_url)


__all__ = ["DatabaseConnection", "db", "get_db_connection"]
