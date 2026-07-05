"""
Database Initialization Script
Creates all tables defined in models.py
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import settings
from database.models import Base, User, QueryHistory, Session


def create_tables():
    """Create all tables in the database"""
    print("\n" + "=" * 80)
    print("DATABASE INITIALIZATION")
    print("=" * 80)

    # Create synchronous engine for table creation
    engine = create_engine(
        settings.database_url,
        echo=settings.DEBUG,
        pool_pre_ping=True
    )

    print(f"\n[1/3] Connecting to database: {settings.DATABASE_NAME}")
    print(f"      Host: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")

    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"[OK] Connected to PostgreSQL")
            print(f"     Version: {version.split(',')[0]}")

        print(f"\n[2/3] Creating tables...")

        # Create all tables
        Base.metadata.create_all(engine)

        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN ('users', 'query_history', 'sessions')
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]

            if len(tables) == 3:
                print(f"[OK] Tables created successfully:")
                for table in tables:
                    print(f"     - {table}")
            else:
                print(f"[WARN] Expected 3 tables, found {len(tables)}: {tables}")

        print(f"\n[3/3] Verifying table structure...")

        with engine.connect() as conn:
            # Check User table
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'users'
                ORDER BY ordinal_position;
            """))
            user_columns = result.fetchall()
            print(f"\n     Users table: {len(user_columns)} columns")
            print(f"     - id, email, password_hash, full_name, is_active, is_admin")
            print(f"     - created_at, updated_at")

            # Check QueryHistory table
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'query_history'
                ORDER BY ordinal_position;
            """))
            history_columns = result.fetchall()
            print(f"\n     QueryHistory table: {len(history_columns)} columns")
            print(f"     - id, user_id, user_query, domain")
            print(f"     - retrieved_tables, anchor_tables, similarity_scores")
            print(f"     - generated_sql, sql_explanation")
            print(f"     - execution_status, result_data, analysis")
            print(f"     - chart_type, chart_config, chart_interpretation")

            # Check Session table
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'sessions'
                ORDER BY ordinal_position;
            """))
            session_columns = result.fetchall()
            print(f"\n     Sessions table: {len(session_columns)} columns")
            print(f"     - id, user_id, token, is_active")
            print(f"     - ip_address, user_agent, expires_at")

        print("\n" + "=" * 80)
        print("[OK] DATABASE INITIALIZATION COMPLETE")
        print("=" * 80)
        print("\nAll tables created successfully!")
        print("You can now proceed to Task 1.2: Authentication System\n")

        return True

    except Exception as e:
        print(f"\n[FAIL] Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        engine.dispose()


def drop_tables():
    """Drop all tables (use with caution!)"""
    print("\n" + "=" * 80)
    print("WARNING: DROPPING ALL TABLES")
    print("=" * 80)

    response = input("\nAre you sure you want to drop all tables? (yes/no): ")
    if response.lower() != "yes":
        print("Operation cancelled.")
        return False

    engine = create_engine(settings.database_url, echo=settings.DEBUG)

    try:
        print("\nDropping tables...")
        Base.metadata.drop_all(engine)
        print("[OK] All tables dropped successfully")
        return True

    except Exception as e:
        print(f"[FAIL] Error dropping tables: {e}")
        return False

    finally:
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop all tables before creating (WARNING: destroys all data)"
    )
    args = parser.parse_args()

    if args.drop:
        if drop_tables():
            create_tables()
    else:
        create_tables()
