#!/usr/bin/env python3
"""
Initialize the Linkd backend database and verify all components.

Usage:
    python init_backend.py
"""

import os
import sys
import logging

# Add parent directory to path so we can import src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize the backend database and verify configuration."""
    logger.info("=" * 60)
    logger.info("Linkd Backend Initialization")
    logger.info("=" * 60)

    # Step 1: Check .env file
    logger.info("\n[Step 1] Checking .env configuration...")
    if not os.path.exists(".env"):
        logger.error("ERROR: .env file not found!")
        logger.error("Please create .env from .env.example and fill in the API keys.")
        return False
    logger.info("✓ .env file exists")

    # Step 2: Load configuration
    logger.info("\n[Step 2] Loading configuration...")
    try:
        from src.config import settings

        logger.info(f"✓ Database URL: {settings.database_url[:50]}...")
        logger.info(f"✓ Deepgram API Key: {settings.deepgram_api_key[:20]}...")
        logger.info(f"✓ Gemini API Key: {settings.gemini_api_key[:20]}...")
    except Exception as e:
        logger.error(f"ERROR: Failed to load configuration: {e}")
        return False

    # Step 3: Test database connection
    logger.info("\n[Step 3] Testing database connection...")
    try:
        from src import db

        with db.engine.connect() as conn:
            result = conn.execute("SELECT 1")
            logger.info("✓ Database connection successful")
    except Exception as e:
        logger.error(f"ERROR: Database connection failed: {e}")
        logger.error("Make sure PostgreSQL is running and DATABASE_URL is correct.")
        return False

    # Step 4: Initialize database
    logger.info("\n[Step 4] Initializing database schema...")
    try:
        db.init_db()
        logger.info("✓ Database schema initialized successfully")
    except Exception as e:
        logger.error(f"ERROR: Database initialization failed: {e}")
        logger.error("Check logs above for details.")
        return False

    # Step 5: Verify tables exist
    logger.info("\n[Step 5] Verifying tables...")
    try:
        from sqlalchemy import text

        tables_to_check = ["users", "user_persona", "interest_nodes", "conversations"]
        with db.engine.connect() as conn:
            for table in tables_to_check:
                result = conn.execute(
                    text(
                        f"SELECT to_regclass('{table}'); "
                    )
                )
                if result.scalar():
                    logger.info(f"✓ Table '{table}' exists")
                else:
                    logger.warning(f"⚠ Table '{table}' not found")
    except Exception as e:
        logger.warning(f"Could not verify tables: {e}")

    # Step 6: Success summary
    logger.info("\n" + "=" * 60)
    logger.info("✅ Backend initialization complete!")
    logger.info("=" * 60)
    logger.info("\nTo start the server, run:")
    logger.info("  uvicorn src.main:app --reload")
    logger.info("\nAPI will be available at: http://localhost:8000")
    logger.info("API docs at: http://localhost:8000/docs")
    logger.info("=" * 60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
