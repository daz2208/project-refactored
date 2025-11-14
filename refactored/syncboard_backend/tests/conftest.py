"""
Shared test fixtures for all test modules.

Provides:
- db_session: SQLite in-memory database session for testing
- Test environment setup (TESTING=true, secrets, etc.)
- Test state cleanup between tests
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# =============================================================================
# Test Environment Configuration
# =============================================================================

# Set test environment variables
os.environ['TESTING'] = 'true'
os.environ['SYNCBOARD_SECRET_KEY'] = os.environ.get('SYNCBOARD_SECRET_KEY', 'test-secret-key-for-testing')
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'sk-test-key')

# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture
def db_session() -> Session:
    """
    Create test database session with in-memory SQLite.

    Used by tests that need direct database access (e.g., analytics tests).
    Creates fresh database with all tables for each test.
    """
    from backend.db_models import Base

    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()
    engine.dispose()


# =============================================================================
# State Cleanup
# =============================================================================

@pytest.fixture
def cleanup_test_state():
    """
    Clean up global state between tests (opt-in).

    Use this fixture explicitly in tests that need state isolation:
        def test_something(cleanup_test_state):
            ...

    Prevents test pollution from shared in-memory state.
    """
    # Setup: Nothing needed before test

    yield  # Test runs here

    # Teardown: Clean up global state after test
    from backend import dependencies

    # Clear in-memory storage
    dependencies.documents.clear()
    dependencies.metadata.clear()
    dependencies.clusters.clear()
    dependencies.users.clear()

    # Clear vector store (only attributes that exist)
    if hasattr(dependencies.vector_store, 'docs'):
        dependencies.vector_store.docs.clear()
    if hasattr(dependencies.vector_store, 'doc_ids'):
        dependencies.vector_store.doc_ids.clear()
    if hasattr(dependencies.vector_store, 'texts'):
        dependencies.vector_store.texts.clear()
    if hasattr(dependencies.vector_store, 'tfidf_matrix'):
        dependencies.vector_store.tfidf_matrix = None
