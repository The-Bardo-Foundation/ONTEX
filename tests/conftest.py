"""
Pytest configuration and fixtures for test suite.
Handles proper cleanup of resources like database connections and event loops.
"""
import pytest
import asyncio
import sys
from pathlib import Path

# Ensure repository root is on sys.path so `import app` works in CI
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    """
    Create a single event loop for the entire test session.
    This prevents event loop issues and ensures proper cleanup.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def cleanup_engines():
    """
    Fixture that automatically runs after each test to ensure
    all SQLAlchemy engines are properly disposed.
    
    This prevents the Python process from hanging due to unclosed
    database connections waiting for cleanup.
    """
    yield
    
    # After test completes, dispose all engines
    # Import here to avoid issues if test hasn't imported the db module
    try:
        from app.db.database import engine
        await engine.dispose()
    except Exception as e:
        print(f"Warning: Error disposing engine in cleanup: {e}")
