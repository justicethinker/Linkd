import os
import pytest
from sqlalchemy import text

from ked.src import db


def test_init_db_creates_tables(tmp_path, monkeypatch):
    # Use a temporary SQLite database for schema creation
    sqlite_url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", sqlite_url)
    # reload settings
    from ked.src.config import settings
    assert settings.database_url == sqlite_url

    # call init_db - should not raise
    db.init_db()

    # basic query to verify tables exist
    with db.engine.connect() as conn:
        res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';")).fetchall()
        names = {r[0] for r in res}
        assert "users" in names
        assert "user_persona" in names
        assert "interest_nodes" in names
        assert "conversations" in names


@pytest.mark.skip("RLS policies require PostgreSQL; run manually against a live DB")
def test_rls_policies_exist():
    # This test is a placeholder demonstrating how one might check the RLS policies.
    with db.engine.connect() as conn:
        res = conn.execute(text("SELECT policyname FROM pg_policies WHERE tablename='user_persona';")).fetchall()
        assert any("user_isolation" in r[0] for r in res)
