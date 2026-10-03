"""Isolated API integration tests, no real Stripe charges or external requests."""
import importlib.util
import os
from pathlib import Path

os.environ['ADMIN_PASSWORD']='strong-testing-password-123'
os.environ['APP_BASE_URL']='http://testserver'

from fastapi.testclient import TestClient
import server


def make_client(tmp_path):
    server.DB_PATH=tmp_path/'koren-test.sqlite3'
    server.init_db()
    return TestClient(server.app)


def logged_in(client):
    assert client.get('/api/admin/products').status_code==401
    wrong=client.post('/api/admin/login',json={'username':'admin','password':'wrong'})
    assert wrong.status_code==401
    response=client.post('/api/admin/login',json={'username':'admin','password':'strong-testing-password-123'})
    assert response.status_code==200
    token=client.get('/api/admin/me').json()['csrf']
    return {'X-CSRF-Token':token}


def sample_order(**overrides):
    result={'customer':{'name':'Тест Клиент','email':'test@example.net','phone':'0888123456',
             'address':'София, Тестова улица 123'},
            'items':[{'id':'apples','quantity':2},{'id':'bread','quantity':1}],
            'payment_method':'cod'}
    result.update(overrides)
    return result


def test_guest_catalog_and_order(tmp_path):
    with make_client(tmp_path) as client:
        products=client.get('/api/products').json()
        assert len(products)==12
        assert client.get('/admin').status_code==200
        assert client.get('/').status_code==200
        assert client.get('/api/config').json()['stripe_enabled'] is False
        assert client.post('/api/orders',json=sample_order(payment_method='stripe')).status_code==400
        tampered=sample_order()
        tampered['items'][0]['price']=0.01 # ignored: trusted prices come from the DB
        created=client.post('/api/orders',json=tampered)
        assert created.status_code==201, created.text
        data=created.json()
        assert data['id'].startswith('K-')
        assert data['total']==12.37
        assert data['payment']=='cod_due'
        assert client.post('/api/orders',json=sample_order(items=[{'id':'apples','quantity':31}])).status_code==409
        assert next(p for p in client.get('/api/products').json() if p['id']=='apples')['stock']==28
        assert client.post('/api/orders',json=sample_order(items=[{'id':'apples','quantity':1}]*2)).status_code==422


def test_admin_auth_products_and_cancel(tmp_path):
    with make_client(tmp_path) as client:
        auth=logged_in(client)
        assert client.post('/api/admin/products',json=client.get('/api/admin/products').json()[0]).status_code==403
        assert client.put('/api/admin/products/apples',headers={},json=client.get('/api/admin/products').json()[0]).status_code==403
        before=client.get('/api/admin/products').json()
        apple=next(p for p in before if p['id']=='apples')
        apple['name']='Нови български ябълки'
        apple['price']='5.55'
        response=client.put('/api/admin/products/apples',json=apple,headers=auth)
        assert response.status_code==200,response.text
        assert client.get('/api/products').json()[0]['price']==5.55
        created=client.post('/api/orders',json=sample_order())
        assert created.status_code==201
        oid=created.json()['id']
        assert created.json()['total']==18.49
        rows=client.get('/api/admin/orders').json()
        assert rows[0]['id']==oid
        assert rows[0]['name']=='Тест Клиент'
        assert client.patch('/api/admin/orders/'+oid,json={'status':'cancelled'},headers=auth).status_code==200
        assert client.patch('/api/admin/orders/'+oid,json={'status':'cancelled'},headers=auth).status_code==409
        assert next(p for p in client.get('/api/products').json() if p['id']=='apples')['stock']==30
        new=client.post('/api/admin/products',json={**apple,'name':'Нов тестов продукт'},headers=auth)
        assert new.status_code==201,new.text
        pid=new.json()['id']
        assert client.delete('/api/admin/products/'+pid,headers=auth).status_code==200
        assert not any(p['id']==pid for p in client.get('/api/products').json())
        assert client.post('/api/admin/logout',headers=auth).status_code==200
        assert client.get('/api/admin/me').status_code==401


def test_mocked_stripe_checkout_and_expiration(tmp_path, monkeypatch):
    """Mock Stripe to test reservation/webhook logic without issuing payment."""
    import sys
    import json
    from types import SimpleNamespace

    fake_stripe=SimpleNamespace(
        checkout=SimpleNamespace(Session=SimpleNamespace(create=lambda **kwargs:SimpleNamespace(
            id='cs_test_mock_001',url='https://checkout.stripe.com/test/mock'))),
        Webhook=SimpleNamespace(construct_event=lambda body, signature, secret:json.loads(body)),
        api_key=None
    )
    monkeypatch.setitem(sys.modules,'stripe',fake_stripe)
    monkeypatch.setattr(server,'STRIPE_ENABLED',True)
    monkeypatch.setattr(server,'STRIPE_SECRET','sk_test_mock')
    monkeypatch.setattr(server,'STRIPE_WEBHOOK_SECRET','whsec_mock')
    with make_client(tmp_path) as client:
        response=client.post('/api/orders',json=sample_order(payment_method='stripe'))
        assert response.status_code==201,response.text
        oid=response.json()['id']
        assert response.json()['checkout_url'].startswith('https://checkout.stripe.com')
        assert next(p for p in client.get('/api/products').json() if p['id']=='apples')['stock']==28
        event={'type':'checkout.session.expired','data':{'object':{
            'client_reference_id':oid,'id':'cs_test_mock_001',
            'metadata':{'order_id':oid},'currency':'eur','amount_total':1237}}}
        assert client.post('/api/stripe/webhook',json=event).status_code==200
        assert client.post('/api/stripe/webhook',json=event).status_code==200
        assert next(p for p in client.get('/api/products').json() if p['id']=='apples')['stock']==30
        auth=logged_in(client)
        row=client.get('/api/admin/orders').json()[0]
        assert row['status']=='expired'
        assert row['payment_state']=='unpaid'


def test_stripe_payment_confirmation_is_webhook_only(tmp_path, monkeypatch):
    """No external Stripe API access; simulate signed events and incorrect totals."""
    import sys
    import json
    from types import SimpleNamespace

    captured = {}
    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(id='cs_test_paid_987', url='https://checkout.stripe.com/test/mock')
    def verify(body, signature, secret):
        if signature!='signed-test' or secret!='whsec_mock':
            raise ValueError('bad signature')
        return json.loads(body)
    fake = SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(create=create)),
                           Webhook=SimpleNamespace(construct_event=verify), api_key=None)
    monkeypatch.setitem(sys.modules,'stripe',fake)
    monkeypatch.setattr(server,'STRIPE_ENABLED',True)
    monkeypatch.setattr(server,'STRIPE_SECRET','sk_test_mock')
    monkeypatch.setattr(server,'STRIPE_WEBHOOK_SECRET','whsec_mock')
    with make_client(tmp_path) as client:
        order=client.post('/api/orders',json=sample_order(payment_method='stripe'))
        assert order.status_code==201
        oid=order.json()['id']
        assert captured['payment_method_types']==['card']
        assert captured['locale']=='bg'
        assert '{CHECKOUT_SESSION_ID}' in captured['success_url']
        assert client.get('/api/checkout/status',params={'session_id':'cs_test_paid_987'}).json()['payment_state']=='pending'
        assert client.get('/api/checkout/status',params={'session_id':'invalid'}).status_code==404
        good={'id':'cs_test_paid_987','client_reference_id':oid,'metadata':{'order_id':oid},
              'currency':'eur','amount_total':1237,'payment_status':'paid'}
        bad_event={'livemode':False,'type':'checkout.session.completed','data':{'object':good}}
        assert client.post('/api/stripe/webhook',json=bad_event).status_code==400
        assert client.get('/api/checkout/status',params={'session_id':'cs_test_paid_987'}).json()['payment_state']=='pending'
        assert client.post('/api/stripe/webhook',json=bad_event,headers={'stripe-signature':'signed-test'}).status_code==200
        paid=client.get('/api/checkout/status',params={'session_id':'cs_test_paid_987'}).json()
        assert paid['payment_state']=='paid'
        assert paid['status']=='new'
        assert paid['id']==oid
        expired={'livemode':False,'type':'checkout.session.expired','data':{'object':good}}
        assert client.post('/api/stripe/webhook',json=expired,headers={'stripe-signature':'signed-test'}).status_code==200
        assert next(p for p in client.get('/api/products').json() if p['id']=='apples')['stock']==28


def test_stripe_wrong_amount_holds_order_for_review(tmp_path, monkeypatch):
    """A signed event is not enough if the Stripe paid amount mismatches our order."""
    import sys, json
    from types import SimpleNamespace
    fake=SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(
        create=lambda **kwargs:SimpleNamespace(id='cs_test_mismatch_001',url='https://checkout.stripe.com/mock'))),
        Webhook=SimpleNamespace(construct_event=lambda body,signature,secret:json.loads(body)), api_key=None)
    monkeypatch.setitem(sys.modules,'stripe',fake)
    monkeypatch.setattr(server,'STRIPE_ENABLED',True)
    monkeypatch.setattr(server,'STRIPE_SECRET','sk_test_mock')
    monkeypatch.setattr(server,'STRIPE_WEBHOOK_SECRET','whsec_mock')
    with make_client(tmp_path) as client:
        order=client.post('/api/orders',json=sample_order(payment_method='stripe'))
        oid=order.json()['id']
        wrong={'livemode':False,'type':'checkout.session.completed','data':{'object':{
            'id':'cs_test_mismatch_001','client_reference_id':oid,'metadata':{'order_id':oid},
            'amount_total':1,'currency':'eur','payment_status':'paid'}}}
        assert client.post('/api/stripe/webhook',json=wrong).status_code==200
        status=client.get('/api/checkout/status',params={'session_id':'cs_test_mismatch_001'}).json()
        assert status['payment_state']=='review'
        assert status['status']=='payment_review'
        assert next(p for p in client.get('/api/products').json() if p['id']=='apples')['stock']==28
