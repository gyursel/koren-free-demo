import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi import HTTPException
import server

pytestmark = pytest.mark.skipif(not os.getenv('KOREN_TEST_POSTGRES_URL'), reason='PostgreSQL integration database not supplied')

def test_concurrent_orders_and_restart_preserve_data():
    server.init_db()
    with server.transaction() as db:
        db.execute('UPDATE products SET stock=? WHERE id=?', (1, 'apples'))
    body = server.OrderInput(customer=server.Customer(name='Test Customer', email='test@example.com', phone='123456789', address='Test address 123'), items=[server.Item(id='apples', quantity=1)])
    def order():
        try:
            return server.create_order(body)
        except HTTPException as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: order(), range(2)))
    assert sum(isinstance(r, dict) for r in results) == 1
    assert 409 in results
    server.init_db()
    server._db_ready = False
    with server.connect() as db:
        assert db.execute('SELECT stock FROM products WHERE id=?', ('apples',)).fetchone()['stock'] == 0
        assert db.execute('SELECT COUNT(*) AS n FROM orders').fetchone()['n'] == 1
