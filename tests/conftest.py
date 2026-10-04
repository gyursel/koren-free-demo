"""Optional PostgreSQL integration isolation; set KOREN_TEST_POSTGRES_URL."""
import os
import uuid
import pytest

@pytest.fixture(autouse=True)
def postgres_isolation(monkeypatch):
    url = os.getenv('KOREN_TEST_POSTGRES_URL')
    if not url:
        yield
        return
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    import server
    schema = 'test_' + uuid.uuid4().hex
    with psycopg.connect(url, autocommit=True) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    monkeypatch.setattr(server, 'DATABASE_URL', make_conninfo(url, options='-c search_path=' + schema))
    monkeypatch.setattr(server, '_db_ready', False)
    try:
        yield
    finally:
        with psycopg.connect(url, autocommit=True) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
