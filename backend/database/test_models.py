"""
Test Database Models
Tests CRUD operations on User, QueryHistory, and Session models
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings
from database.models import User, QueryHistory, Session
from datetime import datetime, timezone, timedelta


def test_models():
    """Test all database models"""
    print("\n" + "=" * 80)
    print("TESTING DATABASE MODELS")
    print("=" * 80)

    # Create engine and session
    engine = create_engine(settings.database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Test 1: Create User
        print("\n[TEST 1] Creating test user...")
        test_user = User(
            email="test@example.com",
            password_hash="$2b$12$test_hash_placeholder",  # This would be a real bcrypt hash
            full_name="Test User",
            is_active=True,
            is_admin=False
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        print(f"[OK] User created: {test_user.email}")
        print(f"     ID: {test_user.id}")
        print(f"     Created: {test_user.created_at}")

        # Test 2: Query User
        print("\n[TEST 2] Querying user by email...")
        queried_user = db.query(User).filter(User.email == "test@example.com").first()
        if queried_user:
            print(f"[OK] User found: {queried_user.email}")
            print(f"     Full name: {queried_user.full_name}")
            print(f"     Is active: {queried_user.is_active}")
        else:
            print("[FAIL] User not found")
            return False

        # Test 3: Create QueryHistory
        print("\n[TEST 3] Creating query history entry...")
        test_query = QueryHistory(
            user_id=test_user.id,
            user_query="What are the total sales by territory?",
            domain="sales",
            retrieved_tables=["sales.salesterritory", "sales.salesorderheader", "sales.customer"],
            anchor_tables=["sales.salesterritory", "sales.salesorderheader", "sales.customer"],
            similarity_scores={"sales.salesterritory": 0.95, "sales.salesorderheader": 0.87},
            generated_sql="SELECT territory, SUM(totaldue) FROM sales.salesorderheader GROUP BY territory",
            sql_explanation="Aggregates total sales amount by territory",
            execution_status="success",
            result_data={"rows": [{"territory": "US", "total": 100000}]},
            row_count=5,
            execution_time_ms=120,
            analysis="Sales are highest in US territory",
            chart_type="bar",
            chart_config={"type": "bar", "data": {}},
            chart_interpretation="The bar chart shows US leading in sales"
        )
        db.add(test_query)
        db.commit()
        db.refresh(test_query)
        print(f"[OK] Query history created")
        print(f"     ID: {test_query.id}")
        print(f"     Query: {test_query.user_query}")
        print(f"     Domain: {test_query.domain}")
        print(f"     Status: {test_query.execution_status}")

        # Test 4: Create Session
        print("\n[TEST 4] Creating session...")
        test_session = Session(
            user_id=test_user.id,
            token="test_jwt_token_placeholder_12345",
            ip_address="127.0.0.1",
            user_agent="Mozilla/5.0 Test Browser",
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        print(f"[OK] Session created")
        print(f"     ID: {test_session.id}")
        print(f"     Token: {test_session.token[:20]}...")
        print(f"     Expires: {test_session.expires_at}")
        print(f"     Is expired: {test_session.is_expired()}")

        # Test 5: Test Relationships
        print("\n[TEST 5] Testing relationships...")
        user_with_relations = db.query(User).filter(User.id == test_user.id).first()
        print(f"[OK] User has {len(user_with_relations.query_history)} query history entries")
        print(f"[OK] User has {len(user_with_relations.sessions)} active sessions")

        # Test 6: Query with filter
        print("\n[TEST 6] Testing query filters...")
        sales_queries = db.query(QueryHistory).filter(QueryHistory.domain == "sales").all()
        print(f"[OK] Found {len(sales_queries)} sales queries")

        active_sessions = db.query(Session).filter(Session.is_active == True).all()
        print(f"[OK] Found {len(active_sessions)} active sessions")

        # Test 7: Update operation
        print("\n[TEST 7] Testing update operation...")
        test_user.full_name = "Updated Test User"
        db.commit()
        db.refresh(test_user)
        print(f"[OK] User updated: {test_user.full_name}")

        # Test 8: Cleanup (delete test data)
        print("\n[TEST 8] Cleaning up test data...")
        db.delete(test_session)
        db.delete(test_query)
        db.delete(test_user)
        db.commit()
        print("[OK] Test data cleaned up")

        print("\n" + "=" * 80)
        print("[OK] ALL MODEL TESTS PASSED")
        print("=" * 80)
        print("\nDatabase models are working correctly!")
        print("Task 1.1 is complete. Ready for Task 1.2: Authentication System\n")

        return True

    except Exception as e:
        print(f"\n[FAIL] Error during testing: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    success = test_models()
    sys.exit(0 if success else 1)
